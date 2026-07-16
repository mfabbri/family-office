foreach($r in "engine","rules","knowledge","workspace"){ $p="../family-office-$r"; if(Test-Path $p){Write-Host "$r OK"}else{Write-Warning "$r MISSING"}}
