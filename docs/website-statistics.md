# Website statistics

The browser script `js/visits.js` counts public pages at vpn.tolf.is through
`POST https://api.tolf.is/analytics/view`. It sends only an event UUID, an allow-listed
page path and a referring domain, with no query parameters, fragments or full URLs.
There are no third-party analytics services. Known bots, DNT/GPC requests, admin
pages and excluded accounts/browsers are not counted. Blocking JavaScript or the
collector can reduce the counts. The figures are not unique people.

Without recognition consent, only page views are recorded. With consent, a random
browser UUID lasts 30 days; a visit UUID changes after 30 minutes of inactivity.
Only keyed hashes of those UUIDs are persisted server-side. The choice lasts 180
days. The preference panel can be reopened from the footer. Refusing recognition
removes the local browser identifier and stops future recognition.

`admin/visits.html` reads `GET /admin/analytics?days=1|7|30|90`, requiring the existing
authenticated session and a live administrator role. It shows totals, daily counts,
pages, referrers and collection start. It exposes no account IDs or browser IDs.
Daily buckets use UTC. Start/last-view timestamps use the viewer's local timezone.

Administrators and the two known owner accounts are excluded server-side. Account
exclusions are frozen as hashes from account numbers 9/user0_ipad and 16/user0 at
initialisation; no IP-based ownership inference is used. An excluded authenticated
page visit and a successful admin statistics load also mark the current browser so
its visits after logout are excluded. A browser can be marked directly at
`https://vpn.tolf.is/?analytics=exclude`; this is a non-secret self-exclusion link.

The collector stores its own SQLite file at `/var/lib/tolf-api/web-analytics.db`
(mode 0600), separate from accounts and billing. Events and browser records are
retained for at most 90 days in reports and purged during active collection at most
hourly. IPs and user-agent strings are never persisted by this module. An ephemeral
minute-keyed IP digest exists in memory only for rate limiting. Infrastructure may
process network metadata independently, as described in the privacy notice.

Install `setup/analytics/tolf_web_analytics.py` beside the API modules and append:

```python
import tolf_web_analytics
tolf_web_analytics.install(app, globals())
```

The existing service user must be able to create the statistics file. Back up the
API entry point before restarting only `tolf-api.service`. VPN servers do not need
to restart. Verify the unauthenticated stats endpoint returns 401, invalid collector
origins return 403, and an existing API health route still responds.

Tests: run `tests/analytics/test_analytics.py` in the API Python environment, and
`node tests/analytics/frontend.cjs` for browser identifier/consent/exclusion behavior.
