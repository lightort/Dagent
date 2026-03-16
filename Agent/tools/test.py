from cdp_target_resolver import resolve_cdp_target

result = resolve_cdp_target(
    remote_debugging_url="http://127.0.0.1:9222",
    target_url="file:///C:/Users/14590/Desktop/Dagent/WebPage/index.html",
)

print(result["target_info"])
print(result["cdp_session"])