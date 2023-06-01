from sentry_sdk.scrubber import EventScrubber

JSON_RPC_AGENTS = ["the-works"]


class SentryScrubber(EventScrubber):
    def scrub_event(self, event):
        if (
            event.get("tags")
            and isinstance(event["tags"], dict)
            and event["tags"].get("scheme_slug") in JSON_RPC_AGENTS
        ):
            self.denylist += ["args", "kwargs", "request_data"]
        self.scrub_request(event)
        self.scrub_extra(event)
        self.scrub_user(event)
        self.scrub_breadcrumbs(event)
        self.scrub_frames(event)
        self.scrub_spans(event)
