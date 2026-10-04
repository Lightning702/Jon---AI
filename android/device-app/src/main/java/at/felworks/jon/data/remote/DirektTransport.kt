package at.felworks.jon.data.remote

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.channels.trySendBlocking
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Call
import okhttp3.Callback
import okhttp3.Response
import java.io.IOException
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.BufferedReader
import java.util.concurrent.TimeUnit

class DirektTransport(private val basis: String) : JonTransport {

    override val name: String = "lokal"

    val basisAdresse: String get() = basis

    private val kurz = OkHttpClient.Builder()
        .followRedirects(false)
        .connectTimeout(2500, TimeUnit.MILLISECONDS)
        .readTimeout(25, TimeUnit.SECONDS)
        .build()

    private val lang = OkHttpClient.Builder()
        .followRedirects(false)
        .connectTimeout(3, TimeUnit.SECONDS)
        .readTimeout(150, TimeUnit.SECONDS)
        .build()

    private val typ = "application/json; charset=utf-8".toMediaType()

    override suspend fun erreichbar(): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            val anfrage = Request.Builder()
                .url("$basis/api/health")
                .get()
                .build()
            kurz.newCall(anfrage).execute().use { it.isSuccessful }
        }.getOrDefault(false)
    }

    override suspend fun senden(
        anfrage: JSONObject,
        art: String,
        id: String,
        schluessel: ByteArray,
        wartezeit: Long,
    ): JSONObject = withContext(Dispatchers.IO) {
        val umschlag = umschlagBauen(anfrage, art, id, schluessel)
        val ruf = Request.Builder()
            .url("$basis/api/handy/gate")
            .post(umschlag.toString().toRequestBody(typ))
            .build()
        warten(kurz.newBuilder().readTimeout(wartezeit, TimeUnit.MILLISECONDS).build().newCall(ruf)).use { antwort ->
            val rumpf = antwort.body?.string().orEmpty()
            if (!antwort.isSuccessful) {
                throw JonFehler(fehlertext(rumpf, antwort.code), antwort.code == 403)
            }
            Krypto.entschluesseln(schluessel, "$art:$id", JSONObject(rumpf)).also {
                check(it.optString("rid") == anfrage.optString("rid")) { "Antwort gehört nicht zu dieser Anfrage." }
            }
        }
    }

    override suspend fun werfen(
        anfrage: JSONObject,
        art: String,
        id: String,
        schluessel: ByteArray,
    ) {
        senden(anfrage, art, id, schluessel, 30_000)
    }

    override fun strom(
        anfrage: JSONObject,
        art: String,
        id: String,
        schluessel: ByteArray,
    ): Flow<JSONObject> = callbackFlow {
        val umschlag = umschlagBauen(anfrage, art, id, schluessel)
        val ruf = Request.Builder().url("$basis/api/handy/gate/stream").post(umschlag.toString().toRequestBody(typ)).build()
        val call = lang.newCall(ruf)
        val leserJob = launch(Dispatchers.IO) {
            try {
                call.execute().use { antwort ->
                    check(antwort.isSuccessful) { "Strom abgelehnt (${antwort.code})" }
                    val leser = antwort.body?.charStream()?.let { BufferedReader(it) } ?: error("Keine Antwort vom Pi.")
                    while (true) {
                        val zeile = leser.readLine() ?: break
                        if (!zeile.startsWith("data:")) continue
                        val roh = zeile.removePrefix("data:").trim()
                        if (roh.isEmpty()) continue
                        val paket = JSONObject(roh)
                        if (paket.has("fehler") && !paket.has("c")) error(paket.optString("fehler"))
                        val teil = Krypto.entschluesseln(schluessel, "$art:$id", paket)
                        check(teil.optString("rid") == anfrage.optString("rid")) { "Antwort gehört nicht zu dieser Anfrage." }
                        if (trySendBlocking(teil).isFailure) break
                    }
                }
                close()
            } catch (e: Exception) { close(e) }
        }
        awaitClose { call.cancel(); leserJob.cancel() }
    }

    private suspend fun warten(call: Call): Response = suspendCancellableCoroutine { continuation ->
        continuation.invokeOnCancellation { call.cancel() }
        call.enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) { if (continuation.isActive) continuation.resumeWithException(e) }
            override fun onResponse(call: Call, response: Response) {
                if (continuation.isActive) continuation.resume(response) { _, value, _ -> value.close() } else response.close()
            }
        })
    }

    override fun schliessen() {
        kurz.dispatcher.executorService.shutdown()
        lang.dispatcher.executorService.shutdown()
    }

    private fun umschlagBauen(
        anfrage: JSONObject,
        art: String,
        id: String,
        schluessel: ByteArray,
    ): JSONObject {
        val kern = Krypto.verschluesseln(schluessel, "$art:$id", anfrage)
        return JSONObject()
            .put("v", 1)
            .put("k", art)
            .put("i", id)
            .put("n", kern.getString("n"))
            .put("c", kern.getString("c"))
    }

    private fun fehlertext(rumpf: String, code: Int): String = runCatching {
        JSONObject(rumpf).optString("detail").ifEmpty { "Fehler $code" }
    }.getOrDefault("Fehler $code")
}
