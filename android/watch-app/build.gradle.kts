import java.security.MessageDigest
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    id("org.jetbrains.kotlin.plugin.compose")
}

val uhrVersion = "1.0.1"
val uhrCode = 2_000_001
val signingFile = file(providers.environmentVariable("JON_SIGNING_PROPERTIES").orElse("${System.getProperty("user.home")}/.android/jon-device-signing.properties").get())
val signingValues = Properties().apply { if (signingFile.isFile) signingFile.inputStream().use { load(it) } }

android {
    namespace = "at.felworks.jon.uhr"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "at.felworks.jon.device"
        minSdk = 30
        targetSdk = 36
        versionCode = uhrCode
        versionName = uhrVersion
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
    }

    buildFeatures {
        compose = true
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
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.wear.compose.material)
    implementation(libs.wear.compose.foundation)
    implementation(libs.wear.tiles)
    implementation(libs.wear.protolayout)
    implementation(libs.wear.input)
    implementation(libs.wear.complications)
    implementation(libs.play.services.wearable)
    implementation(libs.guava.android)
    implementation(libs.okhttp)
}

abstract class UhrAusgabe : DefaultTask() {
    @get:InputFile abstract val apk: RegularFileProperty
    @get:Input abstract val version: Property<String>
    @get:Input abstract val code: Property<Int>
    @get:OutputDirectory abstract val ziel: DirectoryProperty

    @TaskAction
    fun ausfuehren() {
        val ordner = ziel.get().asFile.apply { mkdirs() }
        val apkZiel = File(ordner, "Jon-Uhr-${version.get()}.apk")
        apk.get().asFile.copyTo(apkZiel, true)
        val summe = MessageDigest.getInstance("SHA-256").digest(apkZiel.readBytes()).joinToString("") { "%02x".format(it) }
        File(ordner, "SHA256SUMS.txt").writeText("$summe  ${apkZiel.name}\n")
        File(ordner, "jon-uhr.json").writeText("{\"version\":\"${version.get()}\",\"code\":${code.get()},\"apk\":\"${apkZiel.name}\",\"sha256\":\"$summe\",\"groesse\":${apkZiel.length()}}\n")
    }
}

tasks.register<UhrAusgabe>("uhrAusgabe") {
    group = "jon"
    description = "Baut die signierte APK für Wear-OS-Uhren."
    dependsOn("assembleRelease")
    apk.set(layout.buildDirectory.file("outputs/apk/release/watch-app-release.apk"))
    version.set(uhrVersion)
    code.set(uhrCode)
    ziel.set(layout.projectDirectory.dir("ausgabe"))
}
