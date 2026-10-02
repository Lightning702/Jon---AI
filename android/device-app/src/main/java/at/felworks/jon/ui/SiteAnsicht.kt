package at.felworks.jon.ui

import android.graphics.Color as AndroidColor
import android.util.Base64
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import at.felworks.jon.MainActivity
import at.felworks.jon.core.AppBehaelter
import at.felworks.jon.ki.Arbeitsraum
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.net.URLDecoder
import java.net.URLEncoder

data class SiteWunsch(val quelle: String, val pfad: String, val titel: String, val fertig: kotlinx.coroutines.CompletableDeferred<Unit>)

private val FREMD_ERLAUBT = setOf(
    "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com", "fonts.googleapis.com", "fonts.gstatic.com",
    "cdn.tailwindcss.com", "esm.sh", "code.jquery.com", "images.unsplash.com", "picsum.photos", "fastly.picsum.photos",
)

private fun leer(code: Int) = WebResourceResponse("text/plain", "UTF-8", code, if (code == 404) "Nicht gefunden" else "Gesperrt", emptyMap(), ByteArrayInputStream(byteArrayOf()))

private fun laden(activity: MainActivity, behaelter: AppBehaelter, wunsch: SiteWunsch, basis: String, relativ: String): WebResourceResponse {
    if (relativ.split('/').any { it == ".." }) return leer(403)
    return runCatching {
        if (wunsch.quelle == "handy") {
            val datei = Arbeitsraum.datei(activity, if (basis.isBlank()) relativ else "$basis/$relativ")
            check(datei.isFile)
            WebResourceResponse(Arbeitsraum.mime(datei.name), "UTF-8", 200, "OK", mapOf("Cache-Control" to "no-store"), datei.inputStream())
        } else {
            val ziel = "$basis/$relativ"
            val antwort = runBlocking {
                behaelter.verbindung.geraeteOperation(JSONObject().put("op", "call").put("method", "GET").put("path", "/api/mobile/roh?path=" + URLEncoder.encode(ziel, "UTF-8")).put("binary", true), 30_000)
            }
            val mime = antwort.optString("mime").substringBefore(';').ifBlank { Arbeitsraum.mime(relativ) }
            WebResourceResponse(mime, "UTF-8", 200, "OK", mapOf("Cache-Control" to "no-store"), ByteArrayInputStream(Base64.decode(antwort.getString("data"), Base64.DEFAULT)))
        }
    }.getOrElse { leer(404) }
}

@Composable
fun SiteAnsicht(activity: MainActivity, behaelter: AppBehaelter, wunsch: SiteWunsch, oben: Float, schliessen: () -> Unit) {
    val normal = wunsch.pfad.replace('\\', '/')
    val basis = normal.substringBeforeLast('/', "")
    val start = normal.substringAfterLast('/')
    var titel by remember { mutableStateOf(wunsch.titel.ifBlank { start }) }
    var laedt by remember { mutableStateOf(true) }
    var ansicht by remember { mutableStateOf<WebView?>(null) }
    BackHandler { val w = ansicht; if (w != null && w.canGoBack()) w.goBack() else schliessen() }
    DisposableEffect(Unit) { onDispose { ansicht?.destroy() } }
    Column(Modifier.fillMaxSize().background(Color(0xFF0B0B0C))) {
        Row(Modifier.fillMaxWidth().padding(top = (oben + 8).dp, start = 12.dp, end = 12.dp, bottom = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(42.dp).clip(CircleShape).background(Color(0xFF2F2F2F)).clickable(onClick = schliessen), contentAlignment = Alignment.Center) { Text("✕", color = Color.White, fontSize = 18.sp) }
            Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                Text(titel, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(if (laedt) "Lädt …" else if (wunsch.quelle == "handy") "Auf dem Handy" else "Vom Pi", color = Color(0xFFA3A3A3), fontSize = 12.sp, maxLines = 1)
            }
            Box(Modifier.size(42.dp).clip(CircleShape).background(Color(0xFF2F2F2F)).clickable { laedt = true; ansicht?.reload() }, contentAlignment = Alignment.Center) { Text("⟳", color = Color.White, fontSize = 19.sp) }
        }
        AndroidView(modifier = Modifier.fillMaxSize(), factory = { context ->
            WebView(context).apply {
                layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
                setBackgroundColor(AndroidColor.WHITE)
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                settings.allowFileAccess = false
                settings.allowContentAccess = false
                settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                settings.mediaPlaybackRequiresUserGesture = false
                settings.javaScriptCanOpenWindowsAutomatically = false
                settings.setSupportMultipleWindows(false)
                settings.useWideViewPort = true
                settings.loadWithOverviewMode = true
                webChromeClient = WebChromeClient()
                webViewClient = object : WebViewClient() {
                    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean = request.url.host != "site.jon.local"
                    override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                        val url = request.url
                        if (url.host == "site.jon.local") {
                            val relativ = URLDecoder.decode(url.encodedPath.orEmpty(), "UTF-8").trimStart('/').ifBlank { start }
                            return laden(activity, behaelter, wunsch, basis, relativ)
                        }
                        if (url.scheme == "https" && request.method == "GET" && url.host in FREMD_ERLAUBT) return null
                        return leer(403)
                    }
                    override fun onPageFinished(view: WebView, url: String?) {
                        laedt = false
                        view.title?.takeIf { it.isNotBlank() && !it.startsWith("site.jon.local") }?.let { titel = it }
                    }
                }
                ansicht = this
                loadUrl("https://site.jon.local/" + URLEncoder.encode(start, "UTF-8").replace("+", "%20"))
            }
        })
    }
}
