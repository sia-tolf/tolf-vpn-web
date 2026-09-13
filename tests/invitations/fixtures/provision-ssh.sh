#!/bin/bash
set -euo pipefail

COMMAND="${SSH_ORIGINAL_COMMAND:-}"
UUID_PATTERN='[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
PATTERN="^(create|profile|rotate|delete|grant-moscow|revoke-moscow)[[:space:]]+($UUID_PATTERN)([[:space:]]+(riga|moscow)([[:space:]]+(sr|ru|lv|default))?)?$"
USERNAME_PATTERN='[A-Za-z0-9_.@-]{1,128}'
USERNAME_ACTION_PATTERN="^(create-username|delete-username)[[:space:]]+($USERNAME_PATTERN)$"

if [[ "$COMMAND" =~ $USERNAME_ACTION_PATTERN ]]; then
    exec sudo -n \
        /usr/local/sbin/tolf-provision-root \
        "${BASH_REMATCH[1]}" \
        "${BASH_REMATCH[2]}"
fi

if [[ "$COMMAND" =~ $PATTERN ]]; then
    ACTION="${BASH_REMATCH[1]}"
    ACCOUNT_ID="${BASH_REMATCH[2]}"
    SERVER="${BASH_REMATCH[4]:-riga}"
    LOCAL_ID="${BASH_REMATCH[6]:-}"
    if [ -n "$LOCAL_ID" ]; then
        case "$ACTION" in
            create|profile|rotate)
                exec sudo -n \
                    /usr/local/sbin/tolf-provision-root \
                    "$ACTION" \
                    "$ACCOUNT_ID" \
                    "$SERVER" \
                    "$LOCAL_ID"
                ;;
            *)
                echo '{"status":"error","error":"command not allowed"}'
                exit 1
                ;;
        esac
    fi

    exec sudo -n \
        /usr/local/sbin/tolf-provision-root \
        "$ACTION" \
        "$ACCOUNT_ID" \
        "$SERVER"
fi

echo '{"status":"error","error":"command not allowed"}'
exit 1
