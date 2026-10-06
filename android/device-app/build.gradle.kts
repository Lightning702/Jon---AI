import java.security.MessageDigest
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    id("org.jetbrains.kotlin.plugin.compose")
}

val jonVersion = "1.7.2"
val jonCode = 13
val signingFile = file(providers.environmentVariable("JON_SIGNING_PROPERTIES").orElse("${System.getProperty("user.home")}/.android/jon-device-signing.properties").get())
val signingValues = Properties().apply { if (signingFile.isFile) signingFile.inputStream().use { load(it) } }

android {
    namespace = "at.felworks.jon"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "at.felworks.jon.device"
        minSdk = 26
        targetSdk = 37
        versionCode = jonCode
        versionName = jonVersion

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (signingFile.isFile) create("jonDevice") {
            storeFile = file(signingValues.getProperty("storeFile"))
            storePassword = signingValues.getProperty("storePassword")
            keyAlias = signingValues.getProperty("keyAlias")
            keyPassword = signingValues.getProperty("keyPassword")
        }
    }

    buildTypes {
        debug {
            if (signingFile.isFile) signingConfig = signingConfigs.getByName("jonDevice")
        }
        release {
            if (signingFile.isFile) signingConfig = signingConfigs.getByName("jonDevice")
            optimization {
                enable = true
                keepRules {
                    includeDefault = true
                }
            }
        }
        create("pruefung") {
            initWith(getByName("release"))
            isDebuggable = true
            matchingFallbacks += "release"
        }
    }

    flavorDimensions += "vertrieb"
    productFlavors {
        create("direkt") {
            dimension = "vertrieb"
            buildConfigField("boolean", "SELBST_UPDATE", "true")
            ndk { abiFilters += setOf("arm64-v8a") }
        }
        create("play") {
            dimension = "vertrieb"
            buildConfigField("boolean", "SELBST_UPDATE", "false")
        }
    }


    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    packaging {
        resources {
            excludes += setOf(
                "/META-INF/{AL2.0,LGPL2.1}",
                "/META-INF/INDEX.LIST",
                "/META-INF/DEPENDENCIES",
            )
        }
    }
}


dependencies {
    implementation("com.alphacephei:vosk-android:0.3.75@aar")
    implementation("net.java.dev.jna:jna:5.18.1@aar")
    implementation("com.google.ai.edge.litertlm:litertlm-android:0.17.1")
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.core.splashscreen)
    implementation(libs.androidx.biometric)
    implementation(libs.androidx.fragment)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.camera.core)
    implementation(libs.androidx.camera.camera2)
    implementation(libs.androidx.camera.lifecycle)
    implementation(libs.androidx.camera.view)
    implementation(libs.zxing.core)
    implementation(libs.okhttp)
    debugImplementation(libs.androidx.compose.ui.tooling)
    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
}

abstract class JonAusgabe : DefaultTask() {
    @get:InputFile abstract val apk: RegularFileProperty
    @get:InputFile abstract val bundle: RegularFileProperty
    @get:Input abstract val version: Property<String>
    @get:Input abstract val code: Property<Int>
    @get:OutputDirectory abstract val ziel: DirectoryProperty

    private fun pruefsumme(datei: File): String {
        val summe = MessageDigest.getInstance("SHA-256")
        datei.inputStream().use { strom ->
            val puffer = ByteArray(1 shl 16)
            while (true) {
                val gelesen = strom.read(puffer)
                if (gelesen < 0) break
                summe.update(puffer, 0, gelesen)
            }
        }
        return summe.digest().joinToString("") { "%02x".format(it) }
    }

    @TaskAction
    fun ausfuehren() {
        val ordner = ziel.get().asFile.apply { mkdirs() }
        val v = version.get()
        val apkZiel = File(ordner, "Jon-Geraet-$v.apk")
        val aabZiel = File(ordner, "Jon-Geraet-$v-play.aab")
        apk.get().asFile.copyTo(apkZiel, true)
        bundle.get().asFile.copyTo(aabZiel, true)
        val apkSumme = pruefsumme(apkZiel)
        val aabSumme = pruefsumme(aabZiel)
        File(ordner, "SHA256SUMS.txt").writeText("$apkSumme  ${apkZiel.name}\n$aabSumme  ${aabZiel.name}\n")
        File(ordner, "jon-geraet.json").writeText("{\"version\":\"$v\",\"code\":${code.get()},\"apk\":\"${apkZiel.name}\",\"sha256\":\"$apkSumme\",\"groesse\":${apkZiel.length()}}\n")
    }
}

tasks.register<JonAusgabe>("jonAusgabe") {
    group = "jon"
    description = "Baut die signierte APK zum Selbstinstallieren und das App Bundle für Google Play."
    dependsOn("assembleDirektRelease", "bundlePlayRelease")
    apk.set(layout.buildDirectory.file("outputs/apk/direkt/release/device-app-direkt-release.apk"))
    bundle.set(layout.buildDirectory.file("outputs/bundle/playRelease/device-app-play-release.aab"))
    version.set(jonVersion)
    code.set(jonCode)
    ziel.set(layout.projectDirectory.dir("ausgabe"))
}
