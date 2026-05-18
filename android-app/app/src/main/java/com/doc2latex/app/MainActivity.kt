package com.doc2latex.app

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.chaquo.python.Python
import com.doc2latex.app.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var selectedUri: Uri? = null

    private val pickFile: ActivityResultLauncher<Array<String>> =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
            uri ?: return@registerForActivityResult
            selectedUri = uri
            binding.pathLabel.text = uri.lastPathSegment ?: uri.toString()
            binding.convertButton.isEnabled = true
            setStatus("ready", "Selected: ${uri.lastPathSegment}")
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.pickButton.setOnClickListener {
            pickFile.launch(arrayOf("application/pdf", "image/jpeg", "image/png",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
        }

        binding.convertButton.isEnabled = false
        binding.convertButton.setOnClickListener {
            val uri = selectedUri ?: return@setOnClickListener
            runConversion(uri)
        }
    }

    private fun setStatus(kind: String, message: String) {
        binding.statusLabel.text = message
        binding.statusLabel.contentDescription = "$kind: $message"
    }

    private fun runConversion(uri: Uri) {
        binding.convertButton.isEnabled = false
        setStatus("running", "Converting…")

        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching { convertViaPython(uri) }
            }
            result.onSuccess { json ->
                val outPath = json.optString("out_path")
                val blocks = json.optInt("block_count")
                setStatus("done", "Wrote $blocks blocks → $outPath")
                Toast.makeText(this@MainActivity, "Saved $outPath", Toast.LENGTH_LONG).show()
            }.onFailure { e ->
                setStatus("error", "Failed: ${e.message}")
            }
            binding.convertButton.isEnabled = true
        }
    }

    /**
     * Copy the picked SAF URI into app-private storage (Chaquopy / Python
     * can't read content:// URIs directly), then call into the bundled
     * Python entry function.
     */
    private fun convertViaPython(uri: Uri): JSONObject {
        val cacheDir = File(cacheDir, "doc2latex").apply { mkdirs() }
        val fileName = uri.lastPathSegment?.substringAfterLast('/') ?: "input"
        val inputFile = File(cacheDir, fileName)

        contentResolver.openInputStream(uri).use { input ->
            requireNotNull(input) { "could not open input stream" }
            inputFile.outputStream().use { input.copyTo(it) }
        }

        val outDir = File(filesDir, "converted").apply { mkdirs() }
        val outFile = File(outDir, "${inputFile.nameWithoutExtension}.tex")
        val assetsDir = File(outDir, "${inputFile.nameWithoutExtension}_assets")
        assetsDir.mkdirs()

        val py = Python.getInstance()
        val entry = py.getModule("doc2latex_app").callAttr(
            "convert",
            inputFile.absolutePath,
            outFile.absolutePath,
            assetsDir.absolutePath,
        )
        return JSONObject(entry.toString())
    }
}
