# MIU Trace

근거·시간 정확도·신뢰도를 함께 보여주는 독립 상품 이력 조회 PWA입니다.

## GitHub Pages

`main` 브랜치에 push하면 `.github/workflows/pages.yml`이 `frontend/`을 GitHub Pages에 배포합니다.

Pages는 정적 호스팅이므로 FastAPI와 Dropbox/Google credentials는 실행하지 않습니다. 현재 공개 Pages는 안전한 데모 데이터 모드이며, 실제 데이터 연결은 별도 비공개 API 배포 후 `frontend/config.js`의 `API_BASE_URL`에 연결해야 합니다.

## Local

```powershell
python -m http.server 8080 --directory frontend
```

`http://localhost:8080`에서 확인합니다.

