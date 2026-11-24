$out = "$PSScriptRoot\hw.csv"
"time,cpu_pct,ram_free_gb,gpu_pct,gpu_mem_mb,gpu_temp_c" | Out-File -FilePath $out -Encoding utf8
for ($i = 0; $i -lt 200; $i++) {
    $cpu = (Get-CimInstance Win32_Processor).LoadPercentage
    $ram = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB, 1)
    $g = (& nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader,nounits) -split ',\s*'
    "$(Get-Date -Format HH:mm:ss),$cpu,$ram,$($g[0]),$($g[1]),$($g[2])" | Out-File -FilePath $out -Append -Encoding utf8
    Start-Sleep -Seconds 3
}
