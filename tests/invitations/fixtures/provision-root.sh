#!/bin/bash
set -euo pipefail

DIR='/etc/swanctl/conf.d'
SYNC='/usr/local/sbin/ike-users-sync.sh'
IDENTITY_DIR='/var/lib/ike-users/profiles'
MOBILECONFIG_DIR='/var/lib/ike-users/mobileconfig'
ACCESS_DIR='/var/lib/ike-users/moscow-access'

fail() { printf '{"status":"error","error":"%s"}\n' "$1"; exit 1; }
[ "$(id -u)" -eq 0 ] || fail 'root required'
[ "$#" -ge 2 ] && [ "$#" -le 4 ] || fail 'invalid arguments'
ACTION="$1"
ACCOUNT_ID="$2"
SERVER="${3:-riga}"
LOCAL_ID="${4:-}"
[ "$LOCAL_ID" != default ] || LOCAL_ID=""
if [ "$SERVER" = riga ] && [ -z "$LOCAL_ID" ]; then LOCAL_ID=sr; fi
if [[ "$ACTION" = create-username || "$ACTION" = delete-username ]]; then
    [ "$#" -eq 2 ] || fail 'invalid arguments'
    [[ "$ACCOUNT_ID" =~ ^[A-Za-z0-9_.@-]{1,128}$ ]] || fail 'invalid username'
    case "$ACCOUNT_ID" in
        user0|user0_ipad) fail 'protected VPN user' ;;
    esac
else
    [[ "$ACCOUNT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] || fail 'invalid account id'
fi
[[ "$SERVER" = riga || "$SERVER" = moscow ]] || fail 'invalid server'
case "$ACTION" in
    create|profile|rotate)
        case "$SERVER:$LOCAL_ID" in
            riga:sr|riga:ru|moscow:|moscow:sr|moscow:ru|moscow:lv) ;;
            *) fail 'Local ID is not available for this server' ;;
        esac
        ;;
    *) [ "$#" -le 3 ] || fail 'invalid arguments' ;;
esac

exec 9>/var/lock/tolf-provision.lock
flock -x 9
mkdir -p "$ACCESS_DIR"
chmod 700 "$ACCESS_DIR"
COMPACT="${ACCOUNT_ID//-/}"
COMPACT="${COMPACT,,}"
NEW_USER="user_${COMPACT}"
LEGACY_USER="u_${COMPACT}"
NEW_FILE="$DIR/user-${NEW_USER}.conf"
LEGACY_FILE="$DIR/user-${LEGACY_USER}.conf"
ACCESS_FILE="$ACCESS_DIR/$COMPACT.allow"

find_user() {
    if [ -f "$NEW_FILE" ]; then USER="$NEW_USER"; FILE="$NEW_FILE"; return 0; fi
    if [ -f "$LEGACY_FILE" ]; then USER="$LEGACY_USER"; FILE="$LEGACY_FILE"; return 0; fi
    return 1
}
resolve_user() { find_user || fail 'VPN access not found'; }
read_password() { sed -n 's/^[[:space:]]*secret = "\(.*\)"[[:space:]]*$/\1/p' "$1"; }
reload_creds() { swanctl --load-creds --clear --noprompt >/dev/null 2>&1; }
generate_password() {
    /usr/bin/python3 -c 'import secrets; print("".join(secrets.choice("34679ACDEFHJKMNPRTVWXY") for _ in range(16)))'
}
write_user() {
    local password="$1" temporary
    temporary="$(mktemp "$DIR/.tolf-user.XXXXXX")"
    chmod 600 "$temporary"
    cat > "$temporary" <<EOT
secrets {
    eap-${USER} {
        id = ${USER}
        secret = "${password}"
    }
}
EOT
    mv -f "$temporary" "$FILE"
}
prepare_identity() {
    local suffix directory
    for suffix in '' /moscow; do
        directory="$IDENTITY_DIR$suffix"
        if [ ! -e "$directory/$NEW_USER.identity" ] && [ -f "$directory/$LEGACY_USER.identity" ]; then
            cp -p "$directory/$LEGACY_USER.identity" "$directory/$NEW_USER.identity"
            chmod 600 "$directory/$NEW_USER.identity"
        fi
    done
}
require_server_access() {
    [ "$SERVER" = riga ] || [ -f "$ACCESS_FILE" ] || fail 'Moscow access requires a promo code'
}
credential_response() {
    local password identity_file
    password="$(read_password "$FILE")"
    [ -n "$password" ] || return 1
    identity_file="$IDENTITY_DIR/$USER.identity"
    [ "$SERVER" != moscow ] || identity_file="$IDENTITY_DIR/moscow/$USER.identity"
    TOLF_USER="$USER" \
    TOLF_PASSWORD="$password" \
    TOLF_SERVER="$SERVER" \
    TOLF_LOCAL_ID="$LOCAL_ID" \
    TOLF_IDENTITY_FILE="$identity_file" \
        /usr/bin/python3 -c '
import json, os, shlex

value = {
    "status": "ok",
    "username": os.environ["TOLF_USER"],
    "password": os.environ["TOLF_PASSWORD"],
    "server": os.environ["TOLF_SERVER"],
    "localId": os.environ["TOLF_LOCAL_ID"],
}
path = os.environ["TOLF_IDENTITY_FILE"]
if os.path.isfile(path):
    identity = {}
    with open(path, encoding="utf-8") as source:
        for line in source:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, raw = line.split("=", 1)
            words = shlex.split(raw)
            if len(words) != 1:
                raise SystemExit(1)
            identity[key.strip()] = words[0]
    required = ("PROFILE_UUID", "VPN_UUID", "PROFILE_IDENTIFIER", "VPN_IDENTIFIER")
    if all(identity.get(key) for key in required):
        value["identity"] = {key: identity[key] for key in required}
json.dump(value, __import__("sys").stdout, separators=(",", ":"))
__import__("sys").stdout.write("\n")
'
}

case "$ACTION" in
    create-username)
        USER="$ACCOUNT_ID"
        FILE="$DIR/user-${USER}.conf"

        [ ! -e "$FILE" ] || fail 'VPN user already exists'

        PASSWORD="$(generate_password)"

        if ! write_user "$PASSWORD"; then
            rm -f "$FILE"
            fail 'credential file creation failed'
        fi

        rollback_username_creation() {
            rm -f "$FILE"
            reload_creds || true
            "$SYNC" delete "$USER" >/dev/null 2>&1 || true
        }

        if ! reload_creds; then
            rollback_username_creation
            fail 'credential reload failed; creation rolled back'
        fi

        if ! "$SYNC" push "$USER" >/dev/null 2>&1; then
            rollback_username_creation
            fail 'Moscow synchronization failed; creation rolled back'
        fi

        if ! RESPONSE="$(credential_response)"; then
            rollback_username_creation
            fail 'credential response failed; creation rolled back'
        fi
        printf '%s\n' "$RESPONSE"
        ;;
    delete-username)
        USER="$ACCOUNT_ID"
        FILE="$DIR/user-${USER}.conf"

        if [ ! -f "$FILE" ]; then
            printf '{"status":"ok","username":"%s","alreadyAbsent":true}\n' "$USER"
            exit 0
        fi

        BACKUP="${FILE}.delete-backup.$$"
        cp -p "$FILE" "$BACKUP"

        if ! "$SYNC" delete "$USER" >/dev/null 2>&1; then
            rm -f "$BACKUP"
            fail 'Moscow deletion failed'
        fi

        rm -f "$FILE"

        if ! reload_creds; then
            cp -p "$BACKUP" "$FILE"
            rm -f "$BACKUP"
            reload_creds || true
            "$SYNC" push "$USER" >/dev/null 2>&1 || true
            fail 'credential reload failed; deletion rolled back'
        fi

        rm -f "$BACKUP"
        rm -f \
            "$MOBILECONFIG_DIR/$USER.mobileconfig" \
            "$MOBILECONFIG_DIR/moscow/$USER.mobileconfig" \
            "/var/lib/ike-users/sswan/$USER.sswan" \
            "/var/lib/ike-users/sswan/moscow/$USER.sswan"

        printf '{"status":"ok","username":"%s","alreadyAbsent":false}\n' "$USER"
        ;;
    grant-moscow)
        # A successful retry converges after a lost SSH response or a temporary sync error.
        touch "$ACCESS_FILE"
        chmod 600 "$ACCESS_FILE"
        if find_user; then "$SYNC" push "$USER" >/dev/null 2>&1 || fail 'Moscow synchronization failed'; fi
        echo '{"status":"ok","moscowEnabled":true}'
        ;;
    revoke-moscow)
        rm -f "$ACCESS_FILE"
        "$SYNC" delete "$NEW_USER" >/dev/null 2>&1 || fail 'Moscow deletion failed'
        "$SYNC" delete "$LEGACY_USER" >/dev/null 2>&1 || fail 'Moscow deletion failed'
        echo '{"status":"ok","moscowEnabled":false}'
        ;;
    create)
        require_server_access
        if ! find_user; then
            prepare_identity
            USER="$NEW_USER"
            FILE="$NEW_FILE"
            write_user "$(generate_password)"
        fi
        # Retain credentials on partial failure so a repeated create is safe.
        reload_creds || fail 'credential reload failed'
        "$SYNC" push "$USER" >/dev/null 2>&1 || fail 'Moscow synchronization failed'
        RESPONSE="$(credential_response)" || fail 'credential response failed; retry creation'
        printf '%s\n' "$RESPONSE"
        ;;
    profile)
        require_server_access
        resolve_user
        RESPONSE="$(credential_response)" || fail 'credential response failed'
        printf '%s\n' "$RESPONSE"
        ;;
    rotate)
        require_server_access
        resolve_user
        OLD_PASS="$(read_password "$FILE")"
        [ -n "$OLD_PASS" ] || fail 'VPN password not found'
        NEW_PASS="$(generate_password)"
        while [ "$NEW_PASS" = "$OLD_PASS" ]; do NEW_PASS="$(generate_password)"; done
        BACKUP="${FILE}.rotate-backup.$$"
        cp -p "$FILE" "$BACKUP"
        rollback_rotate() {
            cp -p "$BACKUP" "$FILE"
            rm -f "$BACKUP"
            reload_creds || true
            "$SYNC" push "$USER" >/dev/null 2>&1 || true
        }
        write_user "$NEW_PASS"
        if ! reload_creds; then rollback_rotate; fail 'credential reload failed'; fi
        if ! "$SYNC" push "$USER" >/dev/null 2>&1; then rollback_rotate; fail 'Moscow synchronization failed'; fi
        if ! RESPONSE="$(credential_response)"; then rollback_rotate; fail 'credential response failed; password restored'; fi
        rm -f "$BACKUP"
        printf '%s\n' "$RESPONSE"
        ;;
    delete)
        resolve_user
        BACKUP="${FILE}.delete-backup.$$"
        cp -p "$FILE" "$BACKUP"
        if ! "$SYNC" delete "$USER" >/dev/null 2>&1; then rm -f "$BACKUP"; fail 'Moscow deletion failed'; fi
        rm -f "$FILE"
        if ! reload_creds; then
            cp -p "$BACKUP" "$FILE"
            rm -f "$BACKUP"
            reload_creds || true
            "$SYNC" push "$USER" >/dev/null 2>&1 || true
            fail 'credential reload failed; deletion rolled back'
        fi
        rm -f "$BACKUP"
        if [ "$USER" = "$LEGACY_USER" ]; then prepare_identity; fi
        rm -f \
            "$MOBILECONFIG_DIR/$USER.mobileconfig" \
            "$MOBILECONFIG_DIR/moscow/$USER.mobileconfig" \
            "/var/lib/ike-users/sswan/$USER.sswan" \
            "/var/lib/ike-users/sswan/moscow/$USER.sswan"
        # Account permission and stable profile identifiers survive VPN deletion.
        printf '{"status":"ok","username":"%s"}\n' "$USER"
        ;;
    *) fail 'unsupported operation' ;;
esac
