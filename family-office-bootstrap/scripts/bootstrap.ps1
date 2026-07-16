Write-Host "Validate sibling repositories..."
$repos=@("family-office-engine","family-office-rules","family-office-knowledge","family-office-workspace")
foreach($r in $repos){ if(!(Test-Path "../$r")){ Write-Warning "Missing ../$r" }}
