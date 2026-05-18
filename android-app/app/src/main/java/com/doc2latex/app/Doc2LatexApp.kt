package com.doc2latex.app

import android.app.Application
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class Doc2LatexApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // Start the Chaquopy-bundled CPython runtime once at process start.
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
    }
}
