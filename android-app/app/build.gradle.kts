plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "com.doc2latex.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.doc2latex.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"

        // Chaquopy needs all ABIs the app supports declared up front.
        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
    }
}

chaquopy {
    defaultConfig {
        // Chaquopy ships its own 3.11 runtime for Android.
        version = "3.11"

        pip {
            // Only deps that have ARM/x86_64 wheels on Chaquopy's index.
            // Heavy ML / vision deps are intentionally excluded: torch,
            // opencv, pix2tex, nougat, marker, camelot won't fit / build
            // for Android. The mobile build supports the basic DOCX + PDF
            // text path only.
            install("typer>=0.12")
            install("rich>=13.7")
            install("jinja2>=3.1")
            install("python-docx>=1.1")
            install("Pillow>=10.0")
            install("pymupdf>=1.24")
            install("pdfplumber>=0.11")
        }

        // Ship the local doc2latex package as source so we don't depend on
        // a PyPI release for every commit.
        sourceSets {
            getByName("main") {
                srcDir("../../doc2latex")
            }
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-ktx:1.9.2")
    implementation("androidx.documentfile:documentfile:1.0.1")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
