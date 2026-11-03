"""Metric-only process observations; no commands, prompts, paths or credentials."""
import os


def processes(owned=None):
    owned=owned or {};result=[]
    try:import psutil
    except ImportError:return {'status':'unavailable','processes':[]}
    roots=dict(owned)
    for pid,role in list(owned.items()):
        try:
            for child in psutil.Process(pid).children(recursive=True):roots[child.pid]=role+'_child'
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    # Discover the existing FinScope worker without emitting its command line.
    for proc in psutil.process_iter(['pid','name']):
        try:
            name=(proc.info['name'] or '').lower()
            if 'python' in name and 'finscope.local_worker' in proc.cmdline():roots.setdefault(proc.pid,'worker_existing')
            if 'lm studio' in name or 'llm' in name or name=='lms.exe':
                roots.setdefault(proc.pid,'lmstudio_external_or_unknown')
                for child in proc.children(recursive=True):roots.setdefault(child.pid,'lmstudio_external_or_unknown_child')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    for p in psutil.process_iter(['pid','name']):
        try:
            pid=p.pid;name=(p.info['name'] or '').lower()
            role=roots.get(pid)
            if not role and ('lm studio' in name or 'llm' in name or name=='lms.exe'):role='lmstudio_external_or_unknown'
            if not role:continue
            m=p.memory_info()
            result.append(dict(pid=pid,role=role,working_set=m.rss,private_bytes=getattr(m,'private',None),created=p.create_time()))
        except (psutil.NoSuchProcess,psutil.AccessDenied):continue
    return {'status':'actual','processes':result}


def gpu_processes(pids):
    """Dedicated GPU counter bytes; unsupported/unavailable is never zero."""
    if os.name!='nt':return {'status':'unavailable','processes':[]}
    import subprocess,json,re
    try:
        query="@(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory -ErrorAction Stop | Select-Object Name,DedicatedUsage) | ConvertTo-Json -Compress"
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',query],capture_output=True,text=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if r.returncode:raise ValueError()
        rows=json.loads(r.stdout);rows=rows if isinstance(rows,list) else [rows];totals={}
        for row in rows:
            m=re.search(r'pid_(\d+)_',row['Name']);pid=int(m[1]) if m else None
            if pid in pids:totals[pid]=totals.get(pid,0)+int(row['DedicatedUsage'])
        return {'status':'actual','processes':[{'pid':p,'dedicated_bytes':v} for p,v in totals.items()]}
    except Exception:return {'status':'unavailable','processes':[]}
