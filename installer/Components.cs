using System;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;
using Microsoft.Win32;

internal static class Components
{
    private static string Quote(string path) { return "\"" + path.TrimEnd('\\') + "\""; }

    private static void Run(string executable, string arguments, string root)
    {
        var command = new ProcessStartInfo(executable, arguments)
        { WorkingDirectory = root, UseShellExecute = false, CreateNoWindow = true };
        using (var process = Process.Start(command))
        {
            process.WaitForExit();
            if (process.ExitCode != 0)
                throw new IOException(executable + ": код " + process.ExitCode + ". Проверьте соединение и повторите установку.");
        }
    }

    private static string FindPython(string root)
    {
        foreach (string path in new[] {@"Python\python.exe", @"Python\Scripts\python.exe"})
        {
            string executable = Path.Combine(root, path);
            if (File.Exists(executable)) return executable;
        }
        return null;
    }

    private static string RegisteredPython()
    {
        foreach (RegistryKey hive in new[] {Registry.CurrentUser, Registry.LocalMachine})
        using (var key = hive.OpenSubKey(@"Software\Python\PythonCore\3.12\InstallPath"))
        {
            if (key == null) continue;
            string path = key.GetValue("ExecutablePath") as string;
            if (path != null && File.Exists(path)) return path;
        }
        return null;
    }

    private static string FindOllama(string root)
    {
        string local = Path.Combine(root, @"Ollama\ollama.exe");
        if (File.Exists(local)) return local;
        string installed = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Ollama\ollama.exe");
        return File.Exists(installed) ? installed : null;
    }

    private static void Package(string id, string root)
    {
        Run("winget.exe", "install --id " + id + " --exact --source winget --silent --accept-package-agreements --accept-source-agreements --disable-interactivity", root);
    }

    internal static void Setup(string root, bool python, bool ollama, bool model, bool voice, Action<string> status)
    {
        root = Path.GetFullPath(root);
        string executable = FindPython(root);
        if ((model || voice) && !python && executable == null) throw new IOException("Для выбранных моделей отметьте Python и библиотеки.");
        if (model && !ollama && FindOllama(root) == null) throw new IOException("Для Qwen отметьте Ollama.");
        if (python)
        {
            if (executable == null)
            {
                status("Настраиваю Python 3.12…");
                string registered = RegisteredPython();
                if (registered == null)
                {
                    Package("Python.Python.3.12", root);
                    registered = RegisteredPython();
                }
                if (registered == null) throw new IOException("Python 3.12 отсутствует после установки.");
                Run(registered, "-m venv " + Quote(Path.Combine(root, "Python")), root);
                executable = FindPython(root);
                if (executable == null) throw new IOException("Среда Python не создана.");
            }
            status("Устанавливаю библиотеки Python…");
            Run(executable, "-m pip --isolated install --no-input --disable-pip-version-check --index-url https://pypi.org/simple -r requirements.txt", root);
        }
        if (ollama && FindOllama(root) == null)
        {
            status("Устанавливаю Ollama через Windows Package Manager…");
            Package("Ollama.Ollama", root);
            if (FindOllama(root) == null) throw new IOException("Ollama не найдена после установки.");
        }
        if (voice)
        {
            status("Загружаю Дениса и Whisper…");
            Run(executable, "installer/prepare_models.py", root);
        }
        if (model)
        {
            status("Загружаю Qwen. Это может занять несколько минут…");
            Run(executable, "installer/prepare_models.py --qwen", root);
        }
    }

    internal static void ImportAnthems(string root, string source)
    {
        string target = Path.Combine(root, "round-drops");
        if (!Directory.Exists(source) || Path.GetFullPath(source).Equals(Path.GetFullPath(target), StringComparison.OrdinalIgnoreCase)) return;
        Directory.CreateDirectory(target);
        if ((File.GetAttributes(target) & FileAttributes.ReparsePoint) != 0) throw new IOException("Папка гимнов является ссылкой.");
        foreach (string file in Directory.GetFiles(source))
        {
            string name = Path.GetFileName(file);
            if (!Regex.IsMatch(name, @"^(drop-[0-9]+\.wav|match-(perfect-world|win)\.wav|(kill|ace|menu)\.wav|clips\.json)$", RegexOptions.IgnoreCase)) continue;
            string path = Path.Combine(target, name);
            if (!File.Exists(path)) File.Copy(file, path);
        }
    }
}

