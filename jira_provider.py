import base64
import requests
import db_utils

JIRA_TIMEOUT = 15
# fields we ask Jira for; keep it lean
FIELDS = "summary,status,issuetype,priority,project,duedate"


def get_jira_settings():
    conn = db_utils.get_db_connection()
    s = conn.execute('SELECT jira_url, jira_email, jira_token FROM settings WHERE id = 1').fetchone()
    conn.close()
    return dict(s) if s else {}


def is_configured():
    s = get_jira_settings()
    return bool(s.get('jira_url') and s.get('jira_email') and s.get('jira_token'))


def _auth_header(email, token):
    raw = f"{email}:{token}".encode('utf-8')
    return "Basic " + base64.b64encode(raw).decode('ascii')


def _jira_get(path, params=None):
    """GET a Jira REST path. Returns (data, error); error is None on success."""
    s = get_jira_settings()
    url, email, token = s.get('jira_url'), s.get('jira_email'), s.get('jira_token')
    if not (url and email and token):
        return None, "Jira is not configured. Add your site URL, email, and API token in System Settings."

    base = url.rstrip('/')
    try:
        resp = requests.get(
            base + path,
            headers={'Authorization': _auth_header(email, token), 'Accept': 'application/json'},
            params=params or {},
            timeout=JIRA_TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        return None, f"Could not reach Jira: {e}"

    if resp.status_code == 401:
        return None, "Jira rejected your credentials (401). Check your email and API token."
    if resp.status_code == 403:
        return None, "Jira denied access (403). Your token may lack the required permission."
    if resp.status_code >= 400:
        return None, f"Jira error {resp.status_code}: {resp.text[:200]}"
    try:
        return resp.json(), None
    except ValueError:
        return None, "Jira returned an unexpected (non-JSON) response."


def _simplify_issue(issue, base_url):
    f = issue.get('fields', {}) or {}
    status = f.get('status') or {}
    category = (status.get('statusCategory') or {}).get('key')  # new / indeterminate / done
    return {
        'key': issue.get('key'),
        'summary': f.get('summary'),
        'status': status.get('name'),
        'status_category': category,
        'type': (f.get('issuetype') or {}).get('name'),
        'priority': (f.get('priority') or {}).get('name'),
        'project': (f.get('project') or {}).get('key'),
        'duedate': f.get('duedate'),
        'url': f"{base_url.rstrip('/')}/browse/{issue.get('key')}",
    }


def verify_credentials():
    """Confirm the token authenticates. Returns (account, error).

    The /search/jql endpoint returns 200 with empty results for bad/anonymous auth
    rather than 401, so we validate against /myself, which does 401 properly."""
    return _jira_get('/rest/api/3/myself')


def get_assigned_issues(include_done=False):
    """Issues assigned to the authenticated user. Returns (list, error)."""
    # validate auth first, otherwise a bad token silently yields "no issues"
    _, auth_err = verify_credentials()
    if auth_err:
        return None, auth_err

    s = get_jira_settings()
    jql = "assignee = currentUser()"
    if not include_done:
        jql += " AND statusCategory != Done"
    jql += " ORDER BY updated DESC"

    data, err = _jira_get('/rest/api/3/search/jql',
                          {'jql': jql, 'fields': FIELDS, 'maxResults': 50})
    if err:
        return None, err
    base = s.get('jira_url', '')
    return [_simplify_issue(i, base) for i in data.get('issues', [])], None


def get_boards():
    """List the user's Jira boards. Returns (list, error)."""
    data, err = _jira_get('/rest/agile/1.0/board', {'maxResults': 50})
    if err:
        return None, err
    boards = [{'id': b['id'], 'name': b['name'], 'type': b.get('type')} for b in data.get('values', [])]
    return boards, None


def get_board_issues(board_id, include_done=False):
    """Open issues on a given board (works for kanban and scrum). Returns (list, error)."""
    s = get_jira_settings()
    params = {'fields': FIELDS, 'maxResults': 50}
    if not include_done:
        params['jql'] = "statusCategory != Done"
    data, err = _jira_get(f'/rest/agile/1.0/board/{board_id}/issue', params)
    if err:
        return None, err
    base = s.get('jira_url', '')
    return [_simplify_issue(i, base) for i in data.get('issues', [])], None
