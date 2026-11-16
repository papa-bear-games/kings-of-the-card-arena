"""Claude Code guard hook for every Papa Bear repo (guardrails plan, item 11).

Claude Code runs this before each tool call (a PreToolUse hook in .claude/settings.json) and
passes the call as JSON on stdin. Exit code 2 stops the call and tells Claude why; 0 lets it run.
It stops the few actions nobody can undo by the time Scottie reads about them:

- force-pushing main (or master), deleting tags or releases
- making a repository public
- reading, copying or changing the signing-key folders and key files
- a workflow change that would upload to Play's production track
- a chat message or file write that holds a key or token (private key, GitHub/AWS/Google/Anthropic
  token, connection-string password)
- a chat message or file write that tells Scottie to paste instructions into a project
- a chat message that asks Scottie for an OK, a go or a confirm (standing OK, 2026-11-01)
- a chat message that hands Scottie a build to promote to production without the game's Store art
  check run (release checklist line 17a, 2026-11-01: store pictures, video, feature graphic and icon
  current, and the old ones replaced)
- running adb on the PC while a phone job is busy on the `hive-phones` runner (2026-11-12: a local adb
  started a second adb server and the running sign-in test lost its virtual phone)

Plain Python 3 with no packages, so it runs the same in the cloud and on Scottie's PCs.
Copy this file to .claude/hooks/guard.py and settings.json beside it to .claude/settings.json.
"""
import json
import re
import subprocess
import sys

# Signing folders on Scottie's PC (C:\Users\scott\Repos\GitHub\<game>-signing, papa-bear-games-keys)
# and key files anywhere.
SECRET_PATH = re.compile(
    r"([\w.]-signing(?![\w-])|papa-bear-games-keys|[\w-]\.(keystore|jks)\b|passwords?\.txt\b|"
    r"play-review-account\.txt|wsf-test-account\.txt|service-account[^\s\"']*\.json)", re.I)

BASH_RULES = [
    (re.compile(r"\bgit\s+push\b(?=[^;&|\n]*(\s--force|\s-f\b|\s\+))(?=[^;&|\n]*\b(main|master)\b)"),
     "force-pushing main rewrites everyone's history"),
    # A tag looks like v1.0.0.8 or accounts/1.5.1; deleting a claude/ branch is still fine.
    (re.compile(r"\bgit\s+push\b[^;&|\n]*(\s(--delete|-d)\b[^;&|\n]*\bv?\d+\.\d+|\s:refs/tags/|\s:[\w/-]*v?\d+\.\d+)"),
     "deleting a tag on GitHub"),
    (re.compile(r"\bgh\s+release\s+delete\b"), "deleting a release"),
    (re.compile(r"\bgh\s+repo\s+(delete|archive)\b"), "deleting or archiving a repository"),
    (re.compile(r"(--visibility[\s=]+public|\bvisibility\b.{0,20}\bpublic\b|\bprivate\b[\"']?\s*[:=]\s*false|-f\s+private=false)", re.I),
     "making a repository public"),
]

# Key formats that must never appear in chat or a file Claude writes (gitleaks covers the repo; chat has
# no other guard).
KEY_STRING = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{36,}|"
    r"\bgithub_pat_[A-Za-z0-9_]{50,}|\bAIza[0-9A-Za-z_-]{35}\b|\bsk-ant-[A-Za-z0-9_-]{20,}|"
    r"\bxox[baprs]-[A-Za-z0-9-]{20,}|\b(AccountKey|SharedAccessKey|Password|Pwd)=[^;\s<>*\"']{12,})")

# "paste this into project X" is banned (rules/START-HERE.md): changes go into rules/ instead.
PASTE_ASK = re.compile(
    r"\b(paste|copy)\b[^.\n]{0,60}\b(into|in|to)\b[^.\n]{0,30}"
    r"\b(instructions|(game|claude|hq|master|other)\s+projects?|project\s+x\b)", re.I)

# Asking Scottie for an OK, a go or a confirm is banned (rules/START-HERE.md "NO ASKING", 2026-11-01):
# proceed and report. Passwords, real money, production clicks and truly blocked PC clicks are the only asks.
OK_ASK = re.compile(
    r"\byour\s+(ok|okay|go|go-ahead|approval|confirmation|permission)\s+(is\s+)?needed\b|"
    r"\breply\s+[`\"']?(go|ok|okay|yes)\b[`\"']?\s+(to|and|if)\b|"
    r"\b(may|can|shall|should)\s+i\s+(go\s+ahead|proceed)\b|"
    r"\b(is\s+it\s+)?ok(ay)?\s+(if\s+i|to\s+proceed|to\s+go\s+ahead)\b|"
    r"\bwaiting\s+(on|for)\s+your\s+(ok|okay|go|go-ahead|approval|confirmation)\b|"
    r"\b(want|like)\s+me\s+to\s+(go\s+ahead|proceed)\b", re.I)

# Handing Scottie a build for production (release checklist): the message names the green Store art
# check run (tools/store-art), so no release goes out with old store pictures or videos (2026-11-01).
PRODUCTION_HANDOFF = re.compile(
    r"\b(promote|send|roll\s*out|publish)\b(?:[^.\n]|\.(?=\d)){0,60}\b(to|in|into|on)\s+(the\s+)?(play\s+)?production\b|"
    r"\bready\s+for\s+(your\s+)?production\b|\bproduction\s+(release\s+)?click\b", re.I)
STORE_ART_RUN = re.compile(r"store[\s-]art[\s-]check", re.I)

# Tools that post to the chat; their text is what Scottie reads.
CHAT_TOOL = re.compile(r"^mcp__hearthbot__")
RULES_PATH = re.compile(r"(^|[\\/])(rules|tools[\\/]claude-guard)[\\/]")

PROD_UPLOAD = re.compile(r"\btrack\s*:\s*[\"']?production\b|--track[\s=]+production\b", re.I)

# adb as a command word (start of a command or after ; & | ( ` $( ), bare, with a path, or quoted). A mention
# inside a quoted string, a heredoc or an argument (commit message, grep pattern) is not a run.
ADB_RUN = re.compile(
    r"""(?:^|[;&|(`=\n]|\$\()\s*(?:&\s*|call\s+|sudo\s+|time\s+)?(?:"[^"]*[\\/]adb(?:\.exe)?"|["']?(?:[^\s"';&|]*[\\/])?adb(?:\.exe)?["']?)(?=\s|$|[;&|)])""",
    re.I)
HEREDOC = re.compile(r"<<-?\s*[\"']?(\w+)[\"']?[^\n]*\n.*?\n\s*\1\b", re.S)
QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'")
RUNNER_URL = "orgs/papa-bear-games/actions/runners"


def runs_adb(cmd):
    cmd = HEREDOC.sub("", cmd)
    # keep a quoted path that ends in adb(.exe); blank every other quoted string
    cmd = QUOTED.sub(lambda m: m.group(0) if re.search(r"[\\/]adb(\.exe)?[\"']$", m.group(0), re.I) else '""', cmd)
    return bool(ADB_RUN.search(cmd))


def phone_job_busy():
    """True when the hive-phones runner on The-Hive-One is running a job. Any failure (not Windows, no gh,
    offline, slow, odd answer) says False: the guard never blocks work because it could not check."""
    if sys.platform != "win32":
        return False  # the runner is on The-Hive-One; hive2 has its own adb server
    try:
        out = subprocess.run(
            ["gh", "api", RUNNER_URL, "--jq", '.runners[] | select(.name | startswith("hive-phones")) | .busy'],
            capture_output=True, text=True, timeout=8)
        return out.returncode == 0 and "true" in out.stdout.split()
    except Exception:
        return False


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def text_problem(tool, args):
    """Key strings and paste-asks in chat messages and in files Claude writes."""
    path = str(args.get("file_path") or "")
    if CHAT_TOOL.match(tool):
        paste_checked = True
    elif tool in ("Edit", "Write", "MultiEdit"):
        paste_checked = not RULES_PATH.search(path)  # the rules and this guard quote the banned phrase
    else:
        return None
    text = "\n".join(strings(args))
    if KEY_STRING.search(text):
        return "it holds a key, token or password (keys never go in chat or files)"
    if paste_checked and PASTE_ASK.search(text):
        return ("it tells Scottie to paste instructions into a project; put the change in "
                "papabear-hq rules/ (small PR, merged) instead")
    if CHAT_TOOL.match(tool) and PRODUCTION_HANDOFF.search(text) and not STORE_ART_RUN.search(text):
        return ("it hands Scottie a build for production without the Store art check: run the game's Store art "
                "check workflow on main and link its green run (release checklist line 17a)")
    if CHAT_TOOL.match(tool) and OK_ASK.search(text):
        return ("it asks Scottie for an OK, a go or a confirm; he gave a standing OK on 2026-11-01 "
                "(rules/START-HERE.md \"NO ASKING\"): do it and report the result")
    return None


def problem(call):
    tool = call.get("tool_name", "")
    args = call.get("tool_input") or {}
    found = text_problem(tool, args)
    if found:
        return found
    if tool in ("Bash", "PowerShell"):
        cmd = args.get("command", "")
        if runs_adb(cmd) and phone_job_busy():
            return ("a phone job is running on hive-phones (it shares this PC's adb server, and a second adb "
                    "kills the test's virtual phone, 2026-11-12). Wait for the job to finish, or use the Phone "
                    "adb workflow (phone-adb.yml)")
        for rule, why in BASH_RULES:
            if rule.search(cmd):
                return why
        if SECRET_PATH.search(cmd):
            return "it touches a signing-key folder or key file"
        if PROD_UPLOAD.search(cmd):
            return "it would upload to Play's production track"
        return None
    path = str(args.get("file_path") or args.get("path") or args.get("notebook_path") or "")
    pattern = str(args.get("pattern") or "") if tool == "Glob" else ""
    if SECRET_PATH.search(path) or SECRET_PATH.search(pattern):
        return "it touches a signing-key folder or key file"
    if tool in ("Edit", "Write", "MultiEdit") and re.search(r"\.github[\\/]workflows[\\/]", path):
        new = args.get("content") or args.get("new_string") or ""
        new += "".join(e.get("new_string", "") for e in args.get("edits") or [])
        if PROD_UPLOAD.search(new):
            return "a workflow would upload to Play's production track (Scottie promotes to production himself)"
    return None


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0
    why = problem(call)
    if not why:
        return 0
    print(f"Papa Bear guard stopped this: {why}. If Scottie asked for exactly this, he does it "
          "himself or changes the guard (papabear-hq tools/claude-guard).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
