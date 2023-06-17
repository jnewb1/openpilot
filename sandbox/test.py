from tools.lib.route import Route, RouteName

r = Route("d9df6f87e8feff94|2023-06-16--21-02-09", "/mnt/routes")


for seg in r.segments:
    print(seg)