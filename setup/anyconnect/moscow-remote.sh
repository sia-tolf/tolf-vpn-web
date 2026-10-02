#!/bin/sh
set -eu
# The original pilot commands remain supported. No eval, shell or arbitrary argv.
case "${SSH_ORIGINAL_COMMAND:-}" in
    'tolf-oc-node-health') exec /usr/libexec/tolf-oc-devices health ;;
    'tolf-oc-crl-sync') /usr/bin/tolf-oc-crl-sync >/dev/null; exec /usr/libexec/tolf-oc-devices health ;;
    'tolf-oc-session pilot-tolf')
        occtl -s /var/run/occtl-moscow.socket --json show users >/dev/null
        if occtl -s /var/run/occtl-moscow.socket --json show user pilot-tolf >/dev/null 2>&1; then TOLF_CONNECTED=true
        else TOLF_RC=$?; [ "$TOLF_RC" -eq 2 ] || exit 1; TOLF_CONNECTED=false; fi
        printf '{"status":"ok","username":"pilot-tolf","connected":%s}\n' "$TOLF_CONNECTED"
        exit 0 ;;
    'tolf-oc-mode auto') TOLF_MODE=auto ;;
    'tolf-oc-mode ru') TOLF_MODE=ru ;;
    'tolf-oc-mode lv') TOLF_MODE=lv ;;
    'tolf-oc-mode yt') TOLF_MODE=yt ;;
    *)
        case "${SSH_ORIGINAL_COMMAND:-}" in
            *[!a-z0-9\ -]*) echo '{"status":"error","error":"command_not_allowed"}'; exit 1 ;;
        esac
        set -f
        IFS=' '
        set -- ${SSH_ORIGINAL_COMMAND:-}
        case "${1:-}" in
            tolf-oc-device)
                [ "$#" -eq 3 ]; exec /usr/libexec/tolf-oc-devices set "$2" "$3" ;;
            tolf-oc-device-remove)
                [ "$#" -eq 2 ]; exec /usr/libexec/tolf-oc-devices remove "$2" ;;
            tolf-oc-session)
                [ "$#" -eq 2 ]; exec /usr/libexec/tolf-oc-devices session "$2" ;;
            *) echo '{"status":"error","error":"command_not_allowed"}'; exit 1 ;;
        esac ;;
esac
/usr/bin/tolf-oc-mode "$TOLF_MODE" >/dev/null
printf '{"status":"ok","mode":"%s"}\n' "$TOLF_MODE"
