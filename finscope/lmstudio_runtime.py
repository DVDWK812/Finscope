"""Explicit, bounded local model loading. No server startup, downloads or inference."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from .model_providers import ModelError

GIB=1024**3
CONTEXT_LENGTH=2048
GPU_RATIO='0.5'


def lms_executable():
    executable=shutil.which('lms')
    if not executable:
        candidate=Path.home()/'.lmstudio/bin/lms.exe'
        executable=str(candidate) if candidate.is_file() else None
    if not executable:
        raise ModelError('LM Studio CLI is not installed/on PATH; start the installed app and configure lms',kind='not_configured')
    return executable


def run_lms(arguments,timeout=30):
    try:
        result=subprocess.run([lms_executable(),*arguments],stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',
                              errors='replace',timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired:
        raise ModelError('LM Studio load/estimate timed out; inspect lms ps before another action; no retry',kind='timeout') from None
    except OSError:
        raise ModelError('LM Studio CLI could not start; inspect the local installation',kind='not_configured') from None
    if result.returncode or len(result.stdout)+len(result.stderr)>1024*1024:
        raise ModelError('LM Studio CLI rejected the operation; inspect its local UI/logs; no retry',kind='load_error')
    return result.stdout if '--json' in arguments else result.stdout+'\n'+result.stderr


def system_resources():
    """Available physical RAM and conservative free dedicated GPU memory on Windows."""
    if os.name!='nt':
        raise ModelError('Automatic load resource checks currently require Windows; load manually in LM Studio',kind='resources_unknown')
    import ctypes
    import winreg
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),
                  ('available',ctypes.c_ulonglong),('page_total',ctypes.c_ulonglong),('page_free',ctypes.c_ulonglong),
                  ('virtual_total',ctypes.c_ulonglong),('virtual_free',ctypes.c_ulonglong),('extended',ctypes.c_ulonglong)]
    memory=Memory();memory.length=ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise ModelError('Available physical RAM could not be measured; load was stopped',kind='resources_unknown')
    capacities=[]
    for number in range(32):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r'SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}'+chr(92)+f'{number:04}') as key:
                capacity,_=winreg.QueryValueEx(key,'HardwareInformation.qwMemorySize')
                if type(capacity) is int:capacities.append(capacity)
        except OSError:pass
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
            "@(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction Stop | Select-Object -ExpandProperty DedicatedUsage) | ConvertTo-Json -Compress"],
            capture_output=True,text=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        usage=json.loads(result.stdout)
        if type(usage) is int:usage=[usage]
        if not isinstance(usage,list) or not usage or any(type(v) is not int or v<0 for v in usage):raise ValueError
        # Sum all adapter usage against the largest adapter: deliberately conservative.
        gpu_free=max(0,max(capacities)-sum(usage)) if capacities and not result.returncode else 0
    except (OSError,ValueError,subprocess.TimeoutExpired):
        gpu_free=0
    return {'ram_total':memory.total,'ram_available':memory.available,'gpu_total':max(capacities,default=0),'gpu_available':gpu_free}


def check_resources(estimate,resources):
    cpu=max(0,estimate['total_bytes']-estimate['gpu_bytes'])
    if resources['ram_available']<cpu+6*GIB or resources['gpu_available']<estimate['gpu_bytes']+2*GIB:
        raise ModelError(f"Insufficient resources: RAM {resources['ram_available']/GIB:.2f} GiB available / {(cpu+6*GIB)/GIB:.2f} GiB required; "
                         f"VRAM {resources['gpu_available']/GIB:.2f} GiB available / {(estimate['gpu_bytes']+2*GIB)/GIB:.2f} GiB required. "
                         'Includes 4 GiB RAM reserve + 2 GiB overhead and 2 GiB VRAM reserve; load stopped.',kind='resource_limit')


def gpu_ratio(model):
    return '0.8' if model['size_bytes']<=8*GIB else GPU_RATIO


def cli_model_key(model,runner):
    # Native API variant IDs are not necessarily lms load selectors. Validate
    # the CLI's own local catalog and never accept its interactive fallback.
    try:
        catalog=json.loads(runner(['ls','--json','--llm','--variants'],15))
        rows=[r for r in catalog if r['model']['modelKey']==model['key']]
        if len(rows)!=1:raise ValueError
        row=rows[0];variants=row['variants']
        if (len(variants)!=1 or variants[0]['modelKey']!=model['variant']
                or variants[0].get('deviceIdentifier') or variants[0]['sizeBytes']!=model['size_bytes']):raise ValueError
        return row['model']['modelKey']
    except (KeyError,TypeError,ValueError):
        raise ModelError('CLI model/variant could not be matched uniquely to the local API catalog; select and load the exact file in LM Studio',kind='invalid_registry') from None


def load_model(model,*,explicit=False,runner=run_lms,resources=system_resources):
    if explicit is not True:
        raise ModelError('Loading needs an explicit Load selected model action')
    key=cli_model_key(model,runner)
    ratio=gpu_ratio(model)
    # GGUF does not support vLLM engine configuration/CWD options, including
    # their --no-* forms. Supply neither; no engine script or tools are used.
    args=['load',key,'--context-length',str(CONTEXT_LENGTH),'--gpu',ratio,'--parallel','1','--yes']
    output=runner([*args,'--estimate-only'],30)
    gpu=re.search(r'Estimated GPU Memory:\s*([\d.]+) GiB',output)
    total=re.search(r'Estimated Total Memory:\s*([\d.]+) GiB',output)
    if (not gpu or not total or re.search(r'(?:cannot|may not|not enough|insufficient)',output,re.I)
            or float(total[1])*GIB<model['size_bytes'] or float(gpu[1])>float(total[1])):
        raise ModelError('LM Studio did not provide a safe resource estimate; load was stopped',kind='resource_limit')
    estimate={'gpu_bytes':float(gpu[1])*GIB,'total_bytes':float(total[1])*GIB,'context_length':CONTEXT_LENGTH,'gpu_ratio':ratio}
    snapshot=resources();check_resources(estimate,snapshot)
    runner([*args,'--identifier',model['key'],'--ttl','1800'],180)
    return {'model_key':model['key'],'estimate':estimate,'resources_before_load':snapshot}
