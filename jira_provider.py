import base64
import json
import html as html_lib
import requests
import db_utils

JIRA_TIMEOUT = 20
# fields we ask Jira for on list views
LIST_FIELDS = "summary,status,priority,assignee,reporter,issuetype,updated,created"
DETAIL_FIELDS = "summary,status,priority,assignee,reporter,description,comment"

SETTINGS_COLS = (
    "jira_url, jira_email, jira_token, jira_auth_type, jira_api_version, "
    "jira_filters, jira_tempo_url, jira_high_priority, jira_poll_seconds"
)


def get_jira_settings():
    conn = db_utils.get_db_connection()
    s = conn.execute(f'SELECT {SETTINGS_COLS} FROM settings WHERE id = 1').fetchone()
    conn.close()
    return dict(s) if s else {}


def is_configured():
    s = get_jira_settings()
    return bool(s.get('jira_url') and s.get('jira_token'))


def get_filters_map():
    s = get_jira_settings()
    try:
        return json.loads(s.get('jira_filters') or '{}')
    except (ValueError, TypeError):
        return {}


def _auth_header(s):
    """Bearer PAT (Jira Server/DC) or Basic user:token (Cloud / Server Basic)."""
    auth_type = (s.get('jira_auth_type') or 'bearer').lower()
    token = s.get('jira_token') or ''
    if auth_type == 'basic':
        user = s.get('jira_email') or ''
        raw = f"{user}:{token}".encode('utf-8')
        return "Basic " + base64.b64encode(raw).decode('ascii')
    return f"Bearer {token}"


def _api_version(s):
    return (s.get('jira_api_version') or '2').strip()


def _search_path(s):
    # Cloud v3 replaced /search with /search/jql; Server v2 still uses /search
    return '/rest/api/3/search/jql' if _api_version(s) == '3' else '/rest/api/2/search'


def _jira_get(path, params=None):
    """GET a Jira REST path. Returns (data, error); error is None on success."""
    s = get_jira_settings()
    url, token = s.get('jira_url'), s.get('jira_token')
    if not (url and token):
        return None, "Jira is not configured. Add your site URL and token in System Settings."

    base = url.rstrip('/')
    try:
        resp = requests.get(
            base + path,
            headers={'Authorization': _auth_header(s), 'Accept': 'application/json'},
            params=params or {},
            timeout=JIRA_TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        return None, f"Could not reach Jira: {e}"

    if resp.status_code == 401:
        return None, "Jira rejected your credentials (401). Check your token (and auth type)."
    if resp.status_code == 403:
        return None, "Jira denied access (403). Your token may lack the required permission."
    if resp.status_code >= 400:
        return None, f"Jira error {resp.status_code}: {resp.text[:200]}"
    try:
        return resp.json(), None
    except ValueError:
        return None, "Jira returned an unexpected (non-JSON) response."


def verify_credentials():
    """Confirm the token authenticates. /myself 401s on bad auth (unlike /search/jql,
    which returns 200 with empty results)."""
    s = get_jira_settings()
    return _jira_get(f'/rest/api/{_api_version(s)}/myself')


def _simplify_issue(issue, base_url):
    f = issue.get('fields', {}) or {}
    status = f.get('status') or {}
    category = (status.get('statusCategory') or {}).get('key')  # new / indeterminate / done
    priority = f.get('priority') or {}
    assignee = f.get('assignee') or {}
    reporter = f.get('reporter') or {}
    return {
        'key': issue.get('key'),
        'summary': f.get('summary'),
        'status': status.get('name'),
        'status_category': category,
        'type': (f.get('issuetype') or {}).get('name'),
        'priority': priority.get('name') or 'None',
        'priority_id': int(priority['id']) if priority.get('id') else 999,
        'assignee': assignee.get('displayName') or 'Unassigned',
        'reporter': reporter.get('displayName') or '',
        'updated': f.get('updated'),
        'created': f.get('created'),
        'url': f"{base_url.rstrip('/')}/browse/{issue.get('key')}",
    }


def _search(jql, fields=LIST_FIELDS, max_results=100):
    s = get_jira_settings()
    auth_err = verify_credentials()[1]
    if auth_err:
        return None, auth_err
    data, err = _jira_get(_search_path(s), {'jql': jql, 'fields': fields, 'maxResults': max_results})
    if err:
        return None, err
    base = s.get('jira_url', '')
    return [_simplify_issue(i, base) for i in data.get('issues', [])], None


def get_issues_for_view(view):
    """view is 'mine' (assignee = currentUser) or a key in the saved-filters map."""
    if view == 'mine' or not view:
        return _search("assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC")
    filters = get_filters_map()
    filter_id = filters.get(view)
    if not filter_id:
        return None, f"No Jira filter configured for view '{view}'."
    return _search(f"filter = {filter_id} ORDER BY updated DESC")


def get_assigned_issues(include_done=False):
    """Open issues assigned to the user — used by the Tasks import."""
    jql = "assignee = currentUser()"
    if not include_done:
        jql += " AND statusCategory != Done"
    jql += " ORDER BY updated DESC"
    return _search(jql, max_results=50)


def get_issue_detail(key):
    """Description + recent comments (rendered HTML) for one issue."""
    s = get_jira_settings()
    ver = _api_version(s)
    data, err = _jira_get(f'/rest/api/{ver}/issue/{key}',
                          {'fields': DETAIL_FIELDS, 'expand': 'renderedFields'})
    if err:
        return None, err

    fields = data.get('fields', {}) or {}
    rendered = data.get('renderedFields', {}) or {}

    desc_html = rendered.get('description')
    if not desc_html:
        raw_desc = fields.get('description')
        desc_html = f"<pre>{html_lib.escape(str(raw_desc))}</pre>" if raw_desc else ''

    raw_comments = ((fields.get('comment') or {}).get('comments')) or []
    rendered_comments = ((rendered.get('comment') or {}).get('comments')) or []
    comments = []
    for i, c in enumerate(raw_comments):
        body = None
        if i < len(rendered_comments):
            body = rendered_comments[i].get('body')
        if not body:
            body = f"<pre>{html_lib.escape(str(c.get('body', '')))}</pre>"
        comments.append({
            'author': (c.get('author') or {}).get('displayName') or 'Unknown',
            'created': c.get('created'),
            'bodyHtml': body,
        })
    comments = comments[-10:]  # most recent 10, oldest first

    return {
        'key': data.get('key'),
        'summary': fields.get('summary'),
        'status': (fields.get('status') or {}).get('name') or '',
        'descHtml': desc_html,
        'comments': comments,
        'url': f"{s.get('jira_url', '').rstrip('/')}/browse/{data.get('key')}",
    }, None


def get_boards():
    data, err = _jira_get('/rest/agile/1.0/board', {'maxResults': 50})
    if err:
        return None, err
    return [{'id': b['id'], 'name': b['name'], 'type': b.get('type')} for b in data.get('values', [])], None


def get_board_issues(board_id, include_done=False):
    s = get_jira_settings()
    params = {'fields': LIST_FIELDS, 'maxResults': 50}
    if not include_done:
        params['jql'] = "statusCategory != Done"
    data, err = _jira_get(f'/rest/agile/1.0/board/{board_id}/issue', params)
    if err:
        return None, err
    base = s.get('jira_url', '')
    return [_simplify_issue(i, base) for i in data.get('issues', [])], None
