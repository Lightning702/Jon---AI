(function () {
  window.createPetHarness = function ({ base, say, state, busy, isBusy, activity = () => {} }) {
    let active = "";
    let controller = null;
    let closed = false;
    let contextController = null;
    let lastSuggestion = 0;
    let waiting = null;
    let lastAttached = "";
    const commands = /^\/(hhelp|harness|code|projekt|projekte|aufgaben|hstatus|hstop|erlauben|ablehnen|diff|kontext|privat|ruhe)(?:\s|$)/i;
    const finalStates = new Set(["done", "needs_review", "failed", "cancelled", "interrupted"]);
    const labels = { planning: "Ich plane die nächsten Schritte.", working: "Ich arbeite daran.", verifying: "Ich prüfe das Ergebnis.", waiting_approval: "Ein Befehl wartet auf deine Freigabe.", done: "Aufgabe abgeschlossen.", needs_review: "Es gibt noch offene Prüfpunkte.", failed: "Die Aufgabe konnte nicht abgeschlossen werden.", cancelled: "Aufgabe gestoppt.", interrupted: "Aufgabe unterbrochen." };
    async function request(path, data) {
      const response = await fetch(base + path, { method: data === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" }, body: data === undefined ? undefined : JSON.stringify(data) });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(typeof detail.detail === "string" ? detail.detail : "Jon antwortet mit " + response.status);
      }
      return response.json();
    }
    async function events(path, signal, receive) {
      const response = await fetch(base + path, { signal });
      if (!response.ok || !response.body) {
        const error = new Error("Verbindung nicht verfügbar.");
        error.status = response.status;
        throw error;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      try {
        while (true) {
          const { done, value } = await reader.read();
          buffer += decoder.decode(value, { stream: !done });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";
          for (const part of parts) {
            const line = part.split("\n").find((row) => row.startsWith("data:"));
            if (line) receive(JSON.parse(line.slice(5)));
          }
          if (done) break;
        }
      } finally {
        await reader.cancel().catch(() => {});
        reader.releaseLock();
      }
    }
    function display(task) {
      if (task.id !== active) return;
      activity("coding", task.status);
      waiting = task.pending || null;
      let text = labels[task.status] || "Ich bin an deiner Aufgabe dran.";
      text += "\n" + task.goal;
      if (task.pending) {
        waiting = task.pending;
        text += "\n" + task.pending.args.command + "\nOrdner: " + task.pending.args.cwd;
        text += "\nMit Benutzerrechten, auch außerhalb des Projekts möglich.";
        text += "\n/erlauben " + task.id + " " + task.pending.id + "\n/ablehnen " + task.id + " " + task.pending.id;
        text += "\nHier genügt /ja oder /nein.";
      } else if (finalStates.has(task.status)) {
        text += "\n" + task.summary;
      } else {
        text += "\nSchritt " + task.step + " · " + task.changes.length + " Änderungen";
      }
      say(text, true);
      state(finalStates.has(task.status) ? "" : "thinking");
      if (finalStates.has(task.status)) {
        active = "";
        localStorage.removeItem("mini_jon_task");
        busy(false);
      }
    }
    async function follow(id) {
      if (active === id && controller && !controller.signal.aborted) return;
      if (controller) controller.abort();
      controller = new AbortController();
      const signal = controller.signal;
      active = id;
      localStorage.setItem("mini_jon_task", id);
      busy(true);
      let delay = 1000;
      while (!closed && active === id && !signal.aborted) {
        try {
          await events("/harness/tasks/" + id + "/events", signal, (event) => {
            if (event.type === "snapshot") display(event.task);
            else if (event.type === "approval_required") {
              waiting = event.pending;
              activity("coding", "waiting_approval");
              say("Freigabe für: " + event.pending.args.command + "\nOrdner: " + event.pending.args.cwd + "\n" + event.pending.notice + "\n/ja erlaubt · /nein lehnt ab", true);
            } else if (event.type === "approval_decided") {
              waiting = null;
              activity("coding", "working");
            } else if (event.type === "action") {
              say((event.result.error ? "Ich prüfe den Fehler: " + event.result.error : "Schritt ausgeführt: " + event.tool) + "\n/hstatus " + id, true);
            }
          });
          delay = 1000;
        } catch (error) {
          if (signal.aborted) return;
          if (error.status === 404) {
            active = "";
            localStorage.removeItem("mini_jon_task");
            busy(false);
            say("Der gespeicherte Auftrag ist nicht mehr verfügbar. /aufgaben zeigt den Verlauf.", true);
            return;
          }
          say("Verbindung unterbrochen. Ich verbinde mich erneut. Auftrag: " + id, true);
        }
        if (active === id && !signal.aborted) {
          await new Promise((resolve) => setTimeout(resolve, delay));
          delay = Math.min(30000, delay * 2);
        }
      }
    }
    async function context() {
      let delay = 2000;
      while (!closed) {
        contextController = new AbortController();
        try {
          await events("/mini-jon/agent/events", contextController.signal, (event) => {
            if (event.task_id && event.task_id !== active && event.task_id !== lastAttached) {
              lastAttached = event.task_id;
              void follow(event.task_id);
            }
            if (!active) activity(event.activity || "general", "");
            if (event.suggestion && event.suggestion_id !== lastSuggestion && !isBusy() && !document.hidden) {
              lastSuggestion = event.suggestion_id;
              say(event.suggestion + "\n/ruhe schaltet diese Hinweise leiser.", false);
            }
          });
        } catch (error) {
          if (closed) return;
        }
        await new Promise((resolve) => setTimeout(resolve, delay));
        delay = Math.min(30000, delay * 2);
      }
    }
    async function command(text) {
      if (/^\/mitarbeiten(?:\s|$)/i.test(text.trim())) text = text.trim().replace(/^\/mitarbeiten/i, "/harness");
      if (/^\/(ja|nein)$/i.test(text.trim()) && active && waiting) {
        text = (text.trim().toLowerCase() === "/ja" ? "/erlauben " : "/ablehnen ") + active + " " + waiting.id;
      }
      if (!commands.test(text.trim())) return false;
      try {
        const result = await request("/harness/message", { text, source: "minijon" });
        say(result.text || "Befehl nicht erkannt.", true);
        if (result.task_id) void follow(result.task_id);
      } catch (error) {
        say("Ich erreiche die Aufgabensteuerung gerade nicht: " + error.message, true);
      }
      return true;
    }
    async function cancel() {
      if (!active) return;
      try {
        display(await request("/harness/tasks/" + active + "/cancel", {}));
      } catch (error) {
        say("Stopp nicht bestätigt. Bitte /hstatus " + active + " prüfen.", true);
      }
    }
    const saved = localStorage.getItem("mini_jon_task");
    if (saved) void follow(saved);
    void context();
    window.addEventListener("beforeunload", () => {
      closed = true;
      if (controller) controller.abort();
      if (contextController) contextController.abort();
    });
    return { command, cancel, follow, active: () => Boolean(active) };
  };
})();
