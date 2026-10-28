import azure.functions as func

import handlers

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="kiosk", methods=["GET"])
def kiosk(req: func.HttpRequest) -> func.HttpResponse:
    return handlers.handle_kiosk(req)


@app.route(route="checkin", methods=["POST"])
def checkin(req: func.HttpRequest) -> func.HttpResponse:
    return handlers.handle_checkin(req)


@app.route(route="roster", methods=["GET", "POST", "DELETE"])
def roster(req: func.HttpRequest) -> func.HttpResponse:
    return handlers.handle_roster(req)


@app.route(route="activities", methods=["GET", "POST", "DELETE"])
def activities(req: func.HttpRequest) -> func.HttpResponse:
    return handlers.handle_activities(req)


@app.route(route="checkins", methods=["GET", "DELETE"])
def checkins(req: func.HttpRequest) -> func.HttpResponse:
    return handlers.handle_checkins(req)
