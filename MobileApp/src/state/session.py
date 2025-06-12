import flet_onesignal as fos


jwt_token:      str | None = None
refresh_token:  str | None = None
onesignal_id:   str | None = None
onesignal:      fos.OneSignal | None = None
push_registered: bool = False

# кэш /portfolio
cached_portfolio: list[dict] = []
