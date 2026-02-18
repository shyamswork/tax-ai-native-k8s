Write-Host "🚀 Tax AI Native Deploy (Docker Desktop K8s)" -ForegroundColor Cyan
kubectl delete pod tax-api-7594c67c6b-8qlfh -n tax-ai --force  
docker build -t localhost:5000/tax-calc-api:latest -f infra/docker/Dockerfile . 
../kind load docker-image localhost:5000/tax-calc-api:latest --name tax-ai-demo
kubectl apply -f infra\kubernetes\docker-desktop\tax-api.yaml 
kubectl get pods -n tax-ai -w 
kubectl port-forward svc/tax-api 8080:80 -n tax-ai

$simple = @{ amount=1000000; jurisdictions=@("US");} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/ai-tax" -Method Post -Body $simple -ContentType "application/json"

$complex = @{ amount=3000000; jurisdictions=@("US","CA","UK"); } | ConvertTo-Json 
Invoke-RestMethod -Uri "http://localhost:8080/ai-tax" -Method Post -Body $complex -ContentType "application/json"

