from app.services.focus_service import get_focus_service
from app.services.cowork_service import detect_work_app, get_cowork_service
from app.services.routine_service import get_routine_service, _app_name
from app.services.timeline_service import get_timeline_service
from app.services.show_service import _today_data
from app.services.quickwrite_service import get_quickwrite_service, PROMPTS

f = get_focus_service()
print("Focus start:", f.start(25, "Mathe lernen")["active"], "| goal:", f.state()["goal"])
print("Focus stop worked_minutes:", f.stop().get("worked_minutes"))

print("VS Code:", detect_work_app("main.py - Visual Studio Code"))
print("Word:", detect_work_app("Mein Buch.docx - Word"))
print("Browser (leer):", repr(detect_work_app("YouTube - Google Chrome")))
print("cowork answer accept:", get_cowork_service().answer(True)["mode"])
get_cowork_service().answer(False)

print("app_name:", _app_name("main.py - Projekt - Visual Studio Code"))
print("routine suggestions:", get_routine_service().suggestions())
print("timeline stats:", get_timeline_service().stats())
print("today keys:", list(_today_data().keys()))
print("quickwrite modi:", list(PROMPTS.keys()))
print("ALLE OK")
