using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Windows.Forms;

// Application payload and optional components selected by the user.
internal static class Installer
{
    internal static byte[] Payload()
    {
        using (Stream source = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
        using (MemoryStream target = new MemoryStream())
        { if (source == null) throw new InvalidDataException("Missing package"); source.CopyTo(target); return target.ToArray(); }
    }
    internal static Dictionary<string, byte[]> ReadPackage(byte[] data)
    {
        Dictionary<string, byte[]> files = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);
        long total = 0;
        using (MemoryStream input = new MemoryStream(data))
        using (ZipArchive zip = new ZipArchive(input, ZipArchiveMode.Read))
        {
            foreach (ZipArchiveEntry entry in zip.Entries)
            {
                if (entry.Name.Length == 0) continue;
                string name = entry.FullName.Replace('/', '\\');
                if (name.StartsWith("\\") || name.Contains(":") || name.Contains("..") || name.EndsWith(".") || name.EndsWith(" ")) throw new InvalidDataException("Unsafe package name");
                string[] parts = name.Split('\\');
                foreach (string part in parts) if (part.Length == 0 || part.EndsWith(".") || part.EndsWith(" ")) throw new InvalidDataException("Invalid path component");
                if (parts.Length > 1 && parts[0] != "installer" && parts[0] != "assets") throw new InvalidDataException("Protected directory");
                string ext = Path.GetExtension(name).ToLowerInvariant();
                if (Array.IndexOf(new string[] {".py", ".md", ".txt", ".ico", ".svg", ".exe"}, ext) < 0 && name != "LICENSE") throw new InvalidDataException("Unexpected file type");
                if (ext == ".exe" && name != "JARVIS.exe") throw new InvalidDataException("Unexpected executable");
                if (entry.Length > 10000000 || (total += entry.Length) > 30000000 || files.Count >= 200) throw new InvalidDataException("Package too large");
                using (Stream stream = entry.Open()) using (MemoryStream target = new MemoryStream()) { stream.CopyTo(target); files.Add(name, target.ToArray()); }
            }
        }
        foreach (string name in new string[] {"jarvis_ui.py", "product.py", "LICENSE", "README.md", "JARVIS.exe"}) if (!files.ContainsKey(name)) throw new InvalidDataException("Incomplete package: " + name);
        return files;
    }
    internal static void Install(string destination, Dictionary<string, byte[]> files)
    {
        string root = Path.GetFullPath(destination).TrimEnd('\\');
        if (root.Length == 0 || root == Path.GetPathRoot(root).TrimEnd('\\')) throw new IOException("Choose an application folder, not a drive root.");
        Directory.CreateDirectory(root);
        Dictionary<string, byte[]> backups = new Dictionary<string, byte[]>();
        List<string> created = new List<string>();
        foreach (string name in files.Keys)
        {
            string path = Path.GetFullPath(Path.Combine(root, name));
            if (!path.StartsWith(root + "\\", StringComparison.OrdinalIgnoreCase)) throw new IOException("Path escapes destination.");
            string current = Path.GetDirectoryName(path);
            while (current.Length >= root.Length)
            {
                if (Directory.Exists(current) && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0) throw new IOException("Linked application folders are not supported.");
                current = Path.GetDirectoryName(current); if (current == null) break;
            }
            if (File.Exists(path))
            {
                if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new IOException("Linked files are not supported.");
                using (FileStream probe = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None)) { }
                backups[path] = File.ReadAllBytes(path);
            }
            else created.Add(path);
        }
        try
        {
            foreach (KeyValuePair<string, byte[]> entry in files)
            { string path = Path.Combine(root, entry.Key); Directory.CreateDirectory(Path.GetDirectoryName(path)); File.WriteAllBytes(path, entry.Value); }
        }
        catch
        {
            foreach (KeyValuePair<string, byte[]> old in backups) File.WriteAllBytes(old.Key, old.Value);
            foreach (string path in created) if (File.Exists(path)) File.Delete(path);
            throw;
        }
    }
    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            Dictionary<string, byte[]> files = ReadPackage(Payload());
            if (args.Length == 1 && args[0] == "--verify") return 0;
            if (args.Length == 2 && args[0] == "--test-install")
            {
                string test = Path.GetFullPath(args[1]);
                if (!test.StartsWith(Path.GetTempPath(), StringComparison.OrdinalIgnoreCase)) return 3;
                Install(test, files); return 0;
            }
            Application.EnableVisualStyles();
            Form window = new Form { Text = "JARVIS · Install & Updates", ClientSize = new Size(660, 565), StartPosition = FormStartPosition.CenterScreen, BackColor = Color.FromArgb(18, 23, 32), ForeColor = Color.White, FormBorderStyle = FormBorderStyle.FixedDialog, MaximizeBox = false };
            window.Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            Label title = new Label { Text = "J A R V I S", Font = new Font("Segoe UI", 29, FontStyle.Bold), AutoSize = true, Location = new Point(30, 24) };
            Label info = new Label { Text = "Локальная установка / обновление файлов приложения\nОтметьте компоненты. Для загрузок нужен интернет.", Font = new Font("Segoe UI", 11), AutoSize = true, Location = new Point(34, 95) };
            string existing = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "JARVISASSISTENT");
            string normal = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "JARVISASSISTENT");
            TextBox pathBox = new TextBox { Text = Directory.Exists(existing) ? existing : normal, Location = new Point(34, 165), Width = 495, Font = new Font("Segoe UI", 10) };
            Button browse = new Button { Text = "Папка…", Location = new Point(538, 163), Size = new Size(85, 30) };
            browse.Click += delegate { using (FolderBrowserDialog dialog = new FolderBrowserDialog()) { dialog.SelectedPath = pathBox.Text; if (dialog.ShowDialog(window) == DialogResult.OK) pathBox.Text = dialog.SelectedPath; } };
            string adjacent = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "round-drops");
            string anthemSource = Directory.Exists(adjacent) ? adjacent : Path.Combine(existing, "round-drops");
            var python = new CheckBox { Text = "Python 3.12 и библиотеки", Checked = true, AutoSize = true, Location = new Point(34, 210) };
            var ollama = new CheckBox { Text = "Ollama", Checked = true, AutoSize = true, Location = new Point(34, 240) };
            var model = new CheckBox { Text = "Qwen для локального чата (несколько ГБ)", Checked = true, AutoSize = true, Location = new Point(34, 270) };
            var voice = new CheckBox { Text = "Голос Дениса и распознавание Whisper", Checked = true, AutoSize = true, Location = new Point(34, 300) };
            var anthems = new CheckBox { Text = "Мои гимны из локальной папки round-drops", Checked = Directory.Exists(anthemSource), Enabled = Directory.Exists(anthemSource), AutoSize = true, Location = new Point(34, 330) };
            Label note = new Label { Text = "Перед обновлением закройте JARVIS через трей.\nДля Python и Ollama используется Windows Package Manager.\nГимны берутся из папки рядом с EXE или текущей установки.", AutoSize = true, Location = new Point(34, 375) };
            Label status = new Label { Text = "Пакет приложения проверен.", Size = new Size(585, 38), Location = new Point(34, 438), ForeColor = Color.LightSkyBlue };
            Button install = new Button { Text = "Установить / обновить", Location = new Point(34, 495), Size = new Size(230, 36), BackColor = Color.FromArgb(56, 96, 145), FlatStyle = FlatStyle.Flat };
            bool busy = false;
            window.FormClosing += delegate(object sender, FormClosingEventArgs eventArgs) { if (busy) eventArgs.Cancel = true; };
            install.Click += delegate
            {
                string root = pathBox.Text;
                bool setupPython = python.Checked, setupOllama = ollama.Checked, setupModel = model.Checked, setupVoice = voice.Checked, importAnthems = anthems.Checked;
                busy = true;
                install.Enabled = false;
                status.Text = "Устанавливаю файлы JARVIS…";
                var worker = new System.ComponentModel.BackgroundWorker();
                worker.DoWork += delegate
                {
                    Install(root, files);
                    Components.Setup(root, setupPython, setupOllama, setupModel, setupVoice,
                        message => window.BeginInvoke(new Action(() => status.Text = message)));
                    if (importAnthems) Components.ImportAnthems(root, anthemSource);
                };
                worker.RunWorkerCompleted += delegate(object sender, System.ComponentModel.RunWorkerCompletedEventArgs result)
                {
                    busy = false;
                    install.Enabled = true;
                    if (result.Error == null) status.Text = "Готово. Запускайте JARVIS.exe из выбранной папки.";
                    else
                    {
                        status.Text = "Установка прервана. Готовые компоненты сохранены.";
                        MessageBox.Show(window, result.Error.Message, "JARVIS", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }
                    worker.Dispose();
                };
                worker.RunWorkerAsync();
            };
            window.Controls.AddRange(new Control[] { title, info, pathBox, browse, python, ollama, model, voice, anthems, note, status, install });
            Application.Run(window); return 0;
        }
        catch (Exception error) { if (args.Length == 0) MessageBox.Show(error.Message, "JARVIS package error"); return 1; }
    }
}

