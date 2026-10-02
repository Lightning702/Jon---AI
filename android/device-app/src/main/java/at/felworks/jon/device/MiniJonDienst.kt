package at.felworks.jon.device

import android.app.Activity
import android.app.KeyguardManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.inputmethod.InputMethodManager
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import at.felworks.jon.JonApplication
import at.felworks.jon.MainActivity
import at.felworks.jon.R
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.lang.ref.WeakReference
import kotlin.math.abs

class MiniJonDienst : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val behaelter get() = (application as JonApplication).behaelter
    private val prefs by lazy { getSharedPreferences("mini-jon", MODE_PRIVATE) }
    private lateinit var manager: WindowManager
    private var root: LinearLayout? = null
    private var pet: WebView? = null
    private var params: WindowManager.LayoutParams? = null
    private var answer: TextView? = null
    private var send: Button? = null
    private var approvals: LinearLayout? = null
    private var job: Job? = null
    private var expanded = false
    private var lastAnswer = "Ich bin da. Tippe mich an oder zieh mich an einen anderen Platz."
    private var registered = false
    private var pendingApproval: JSONObject? = null
    private val screen = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action == Intent.ACTION_SCREEN_OFF) {
                if (expanded) show(false)
                root?.visibility = View.GONE
                pet?.onPause()
            } else if (!(getSystemService(KEYGUARD_SERVICE) as KeyguardManager).isKeyguardLocked) {
                root?.visibility = View.VISIBLE
                pet?.onResume()
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        manager = getSystemService(WINDOW_SERVICE) as WindowManager
        val notifications = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        notifications.createNotificationChannel(NotificationChannel("mini-jon", "Funke", NotificationManager.IMPORTANCE_LOW))
        val open = PendingIntent.getActivity(this, 881, Intent(this, MainActivity::class.java).putExtra("oeffnen", "minijon"), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val stop = PendingIntent.getService(this, 882, Intent(this, MiniJonDienst::class.java).setAction("stop"), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notice = NotificationCompat.Builder(this, "mini-jon").setSmallIcon(R.drawable.ic_mikro).setContentTitle("Funke ist bei dir")
            .setContentText("Antippen zum Öffnen · jederzeit ausblendbar").setContentIntent(open).setOngoing(true)
            .addAction(0, "Ausblenden", stop).build()
        if (Build.VERSION.SDK_INT >= 34) startForeground(883, notice, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE) else startForeground(883, notice)
        ContextCompat.registerReceiver(this, screen, IntentFilter().apply { addAction(Intent.ACTION_SCREEN_OFF); addAction(Intent.ACTION_USER_PRESENT); addAction(Intent.ACTION_SCREEN_ON) }, ContextCompat.RECEIVER_NOT_EXPORTED)
        registered = true
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "stop" || !prefs.getBoolean("enabled", false) || !Settings.canDrawOverlays(this)) {
            if (intent?.action == "stop") prefs.edit().putBoolean("enabled", false).apply()
            stopSelf()
            return START_NOT_STICKY
        }
        val target = fenster()
        val token = if (target == MiniJonFenster.APP) host.get()?.window?.decorView?.windowToken else null
        val type = if (target == MiniJonFenster.APP) WindowManager.LayoutParams.TYPE_APPLICATION_PANEL else WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        if (target == MiniJonFenster.WARTEN) entfernen()
        else if (root == null || params?.type != type || params?.token != token) show(expanded)
        running = true
        return START_STICKY
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun fenster() = MiniJonFenster.waehlen(GeraeteModus(this).abgeschottet, host.get()?.window?.decorView?.isAttachedToWindow == true, Settings.canDrawOverlays(this))
    private fun entfernen() {
        root?.let { runCatching { manager.removeView(it) } }
        pet?.destroy()
        root = null
        pet = null
        answer = null
        approvals = null
        send = null
    }
    private fun rounded(color: Int, radius: Int = 24) = GradientDrawable().apply { setColor(color); cornerRadius = dp(radius).toFloat() }
    private fun button(label: String, action: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        setTextColor(Color.rgb(255, 218, 137))
        background = rounded(Color.rgb(39, 35, 29), 14)
        setOnClickListener { action() }
        minHeight = dp(44)
        minimumWidth = 0
    }

    private fun show(open: Boolean) {
        val target = fenster()
        val old = params
        entfernen()
        if (target == MiniJonFenster.WARTEN) return
        expanded = open
        val view = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; if (open) { background = rounded(Color.rgb(20, 21, 25)); setPadding(dp(14), dp(10), dp(14), dp(14)); elevation = dp(16).toFloat() } }
        val bounds = resources.displayMetrics
        val width = if (open) minOf(dp(352), bounds.widthPixels - dp(16)) else dp(104)
        val height = if (open) minOf(dp(440), bounds.heightPixels - dp(80)) else dp(112)
        val flags = WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED or if (open) 0 else WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
        val type = if (target == MiniJonFenster.APP) WindowManager.LayoutParams.TYPE_APPLICATION_PANEL else WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        val p = WindowManager.LayoutParams(width, height, type, flags, PixelFormat.TRANSLUCENT).apply {
            if (target == MiniJonFenster.APP) token = host.get()?.window?.decorView?.windowToken
            gravity = Gravity.TOP or Gravity.LEFT
            x = (old?.x ?: prefs.getInt("x", bounds.widthPixels - dp(112))).coerceIn(0, maxOf(0, bounds.widthPixels - width))
            y = (old?.y ?: prefs.getInt("y", dp(220))).coerceIn(dp(24), maxOf(dp(24), bounds.heightPixels - height - dp(48)))
            softInputMode = WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
        }
        params = p
        root = view
        val web = WebView(this).apply {
            setBackgroundColor(Color.TRANSPARENT)
            settings.javaScriptEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.blockNetworkLoads = true
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView?, url: String?) { animate(job?.isActive == true) }
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?) = true
                override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest?): WebResourceResponse {
                    val uri = request?.url
                    val name = uri?.path?.removePrefix("/")
                    if (uri?.host == "minijon.local" && name in setOf("index.html", "funke.js")) {
                        return WebResourceResponse(if (name == "funke.js") "text/javascript" else "text/html", "UTF-8", assets.open("mini-jon/$name"))
                    }
                    return WebResourceResponse("text/plain", "UTF-8", ByteArrayInputStream(ByteArray(0)))
                }
            }
            loadUrl("https://minijon.local/index.html")
            contentDescription = "Funke. Antippen zum Sprechen, ziehen zum Verschieben."
        }
        pet = web
        view.addView(web, LinearLayout.LayoutParams(if (open) dp(90) else width, dp(108)).apply { gravity = Gravity.CENTER_HORIZONTAL })
        drag(web)
        if (open) {
            val controls = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            controls.addView(button("Jon öffnen") { startActivity(Intent(this, MainActivity::class.java).putExtra("oeffnen", "minijon").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); show(false) }, LinearLayout.LayoutParams(0, dp(44), 1f))
            controls.addView(button("Klein") { show(false) }, LinearLayout.LayoutParams(dp(80), dp(44)))
            view.addView(controls)
            val text = TextView(this).apply { setTextColor(Color.rgb(241, 238, 231)); textSize = 15f; setTextIsSelectable(true); setPadding(0, dp(12), 0, dp(12)); text = lastAnswer }
            answer = text
            view.addView(ScrollView(this).apply { addView(text) }, LinearLayout.LayoutParams(-1, 0, 1f))
            approvals = LinearLayout(this).also { view.addView(it) }
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            val input = EditText(this).apply { hint = "Aufgabe für Funke …"; setHintTextColor(Color.GRAY); setTextColor(Color.WHITE); textSize = 15f; maxLines = 3; inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES; filters = arrayOf(android.text.InputFilter.LengthFilter(4000)); setPadding(dp(10), dp(4), dp(10), dp(4)) }
            row.addView(input, LinearLayout.LayoutParams(0, -2, 1f))
            send = button(if (job?.isActive == true) "Stopp" else "Los") { if (job?.isActive == true) { job?.cancel() } else { val question = input.text.toString().trim(); if (question.isNotEmpty()) { input.setText(""); (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).hideSoftInputFromWindow(input.windowToken, 0); ask(question) } } }
            row.addView(send, LinearLayout.LayoutParams(dp(66), dp(48)))
            view.addView(row)
        } else { answer = null; approvals = null; send = null }
        try { manager.addView(view, p) } catch (_: Exception) { root = null; stopSelf() }
        if (open) pendingApproval?.let { approval(it) }
        if ((getSystemService(KEYGUARD_SERVICE) as KeyguardManager).isKeyguardLocked) { view.visibility = View.GONE; web.onPause() }
    }

    private fun drag(view: View) {
        var x = 0f; var y = 0f; var startX = 0; var startY = 0; var moved = false
        view.setOnTouchListener { _, event ->
            val p = params ?: return@setOnTouchListener false
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> { x = event.rawX; y = event.rawY; startX = p.x; startY = p.y; moved = false }
                MotionEvent.ACTION_MOVE -> {
                    val dx = event.rawX - x; val dy = event.rawY - y
                    if (abs(dx) + abs(dy) > dp(8)) moved = true
                    if (moved) {
                        val bounds = resources.displayMetrics
                        p.x = (startX + dx.toInt()).coerceIn(0, maxOf(0, bounds.widthPixels - p.width))
                        p.y = (startY + dy.toInt()).coerceIn(dp(24), maxOf(dp(24), bounds.heightPixels - p.height - dp(48)))
                        root?.let { runCatching { manager.updateViewLayout(it, p) } }
                    }
                }
                MotionEvent.ACTION_UP -> { if (moved) prefs.edit().putInt("x", p.x).putInt("y", p.y).apply() else show(!expanded) }
            }
            true
        }
    }

    private fun display(text: String) { lastAnswer = text; answer?.text = text }
    private fun animate(working: Boolean) {
        pet?.evaluateJavascript("window.setMiniJonState(" + JSONObject.quote(if (working) "working" else "idle") + ")", null)
    }

    private fun ask(question: String) {
        if (job?.isActive == true) return
        approvals?.removeAllViews()
        job = scope.launch {
            send?.text = "Stopp"
            animate(true)
            display("Ich denke nach …")
            val server = behaelter.verbindung.aktuell?.pcId.orEmpty()
            val historyKey = "history_$server"
            val conversationKey = "conversation_$server"
            val messages = runCatching { JSONArray(prefs.getString(historyKey, "[]")) }.getOrDefault(JSONArray())
            messages.put(JSONObject().put("role", "user").put("content", question))
            val body = KinderModus.anfrage(this@MiniJonDienst, JSONObject().put("messages", messages).put("persona", "funke").put("source", "handy").put("persist", true).put("tool_mode", "ask"))
            prefs.getString(conversationKey, null)?.takeIf { it.isNotBlank() }?.let { body.put("conversation_id", it) }
            val result = StringBuilder()
            var finished = false
            try {
                withTimeout(240_000) {
                    withContext(Dispatchers.IO) {
                        behaelter.verbindung.strom("/api/chat", body).collect { chunk ->
                            withContext(Dispatchers.Main) {
                                when (chunk.optString("type")) {
                                    "meta" -> chunk.optString("conversation_id").takeIf { it.isNotBlank() && it != "null" }?.let { prefs.edit().putString(conversationKey, it).apply() }
                                    "content" -> { result.append(chunk.optString("delta")); display(result.toString()) }
                                    "error" -> error(chunk.optString("message", chunk.optString("error", "Jon konnte nicht antworten.")))
                                    "done" -> finished = true
                                    "tool" -> if (chunk.optString("approval_id").isNotBlank()) approval(chunk)
                                }
                            }
                        }
                    }
                }
                check(finished && result.isNotBlank()) { "Die Antwort wurde unterbrochen. Bitte erneut versuchen." }
                messages.put(JSONObject().put("role", "assistant").put("content", result.toString().take(16000)))
                val recent = JSONArray()
                for (i in maxOf(0, messages.length() - 20) until messages.length()) recent.put(messages.get(i))
                prefs.edit().putString(historyKey, recent.toString()).apply()
            } catch (e: CancellationException) { display(if (result.isEmpty()) "Angehalten." else "$result\n\nAngehalten."); throw e }
            catch (e: Exception) { display((if (result.isNotEmpty()) "$result\n\n" else "") + (e.message ?: "Pi nicht erreichbar. Prüfe die Verbindung in Jon.")) }
            finally { send?.text = "Los"; pendingApproval = null; approvals?.removeAllViews(); animate(false) }
        }
    }

    private fun approval(chunk: JSONObject) {
        pendingApproval = chunk
        val id = chunk.optString("id", chunk.optString("approval_id"))
        if (id.isBlank()) return
        display("Freigabe nötig: " + chunk.optString("name", chunk.optString("tool")) + "\n" + (chunk.opt("args")?.toString() ?: "").take(1800))
        approvals?.removeAllViews()
        for ((label, allow) in listOf("Erlauben" to true, "Ablehnen" to false)) {
            approvals?.addView(button(label) {
                approvals?.removeAllViews()
                scope.launch {
                    try { withContext(Dispatchers.IO) { behaelter.verbindung.objekt("POST", "/api/chat/approve", JSONObject().put("id", id).put("approved", allow)) }; pendingApproval = null; display(if (allow) "Freigegeben. Ich arbeite weiter …" else "Abgelehnt.") }
                    catch (e: Exception) { approval(chunk); display(e.message ?: "Freigabe konnte nicht gesendet werden.") }
                }
            }, LinearLayout.LayoutParams(0, dp(44), 1f))
        }
    }

    override fun onConfigurationChanged(newConfig: Configuration) { super.onConfigurationChanged(newConfig); if (root != null) show(expanded) }

    override fun onDestroy() {
        running = false
        scope.cancel()
        if (registered) unregisterReceiver(screen)
        entfernen()
        stopForeground(STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }

    companion object {
        private var host = WeakReference<Activity>(null)
        @Volatile private var running = false
        fun attach(activity: Activity) {
            host = WeakReference(activity)
            activity.window.decorView.post { if (host.get() === activity && !activity.isFinishing && !activity.isDestroyed) refresh(activity) }
        }
        fun detach(activity: Activity) {
            if (host.get() === activity) { host.clear(); refresh(activity) }
        }
        private fun refresh(context: Context) {
            if (status(context).optBoolean("enabled") && Settings.canDrawOverlays(context)) ContextCompat.startForegroundService(context, Intent(context, MiniJonDienst::class.java))
        }
        fun status(context: Context) = JSONObject().put("enabled", context.getSharedPreferences("mini-jon", MODE_PRIVATE).getBoolean("enabled", false)).put("permission", Settings.canDrawOverlays(context)).put("running", running)
        fun enable(context: Context, enabled: Boolean): JSONObject {
            context.getSharedPreferences("mini-jon", MODE_PRIVATE).edit().putBoolean("enabled", enabled).commit()
            if (!enabled) context.stopService(Intent(context, MiniJonDienst::class.java))
            else if (Settings.canDrawOverlays(context)) ContextCompat.startForegroundService(context, Intent(context, MiniJonDienst::class.java))
            else context.startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}")))
            return status(context)
        }
        fun resume(context: Context) { if (status(context).optBoolean("enabled") && Settings.canDrawOverlays(context) && !running) ContextCompat.startForegroundService(context, Intent(context, MiniJonDienst::class.java)) }
    }
}
