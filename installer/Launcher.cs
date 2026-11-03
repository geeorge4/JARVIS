using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
internal static class Launcher
{
    [STAThread] private static int Main(string[] args)
    {
        string root=AppDomain.CurrentDomain.BaseDirectory;
        string python=Path.Combine(root,"Python","pythonw.exe");
        if(!File.Exists(python)) python=Path.Combine(root,"Python","Scripts","pythonw.exe");
        string script=Path.Combine(root,"jarvis_ui.py");
        bool check=args.Length==1 && args[0]=="--check";
        if(!File.Exists(python)||!File.Exists(script))
        {
            if(!check) MessageBox.Show("Python или файлы JARVIS не найдены. Следуйте разделу первого запуска в README.md рядом с JARVIS.exe.","JARVIS",MessageBoxButtons.OK,MessageBoxIcon.Information);
            return 1;
        }
        if(check) return 0;
        try { Process.Start(new ProcessStartInfo {FileName=python,Arguments="\""+script+"\"",WorkingDirectory=root,UseShellExecute=false,CreateNoWindow=true});return 0; }
        catch(Exception error) { MessageBox.Show(error.Message,"JARVIS");return 2; }
    }
}
