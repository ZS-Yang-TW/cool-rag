# **COOL RAG Assistant**

NTU COOL 文件智能問答助理 - 基於 RAG (Retrieval-Augmented Generation) 技術的文件檢索與問答系統。

## **📋 系統需求**

- Docker & Docker Compose
- OpenAI API Key
- PostgreSQL 15+ (with pgvector extension)

## **🚀 快速開始**

### **1. Clone 專案**

```bash
git clone <repository-url>
cd cool-rag
```

### **2. 環境變數設定**

複製環境變數範本：

```bash
cp .env.example .env
```

編輯 `.env` 檔案，填入必要資訊。

### **3. 新增資料庫 && 資料庫遷移**

1. 建立 `cool_rag` 資料庫。
    
    ```sql
    CREATE DATABASE cool_rag;
    
    ```
    
2. 啟用 pgvector 擴充功能。

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### **4. 安裝套件**

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**

```bash
cd frontend
npm install
```

### **5. 資料庫遷移**

請在 `backend` 目錄下執行 migration

```bash
cd backend && alembic upgrade head
```

### **6. 啟動服務**

Backend:

```bash
cd backend && ./start.sh
```

Frontend:

```bash
cd frontend && npm run dev
```

### **6. 文件索引**

將 Markdown 文件放入 `backend/documents/` 目錄後，透過 API 同步並建立索引：

```bash
# 同步文件
curl -X POST http://localhost:8000/api/documents/sync

# 建立索引
curl -X POST http://localhost:8000/api/reindex/selective
```

或使用前端介面的「文件管理」功能進行操作。

### **7. 訪問應用**

- **前端**: [http://localhost:3000](http://localhost:3000/)
- **後端 API 文件**: http://localhost:8000/docs
- **健康檢查**: http://localhost:8000/api/health

## **🎨 UI 客製化**

前端介面的文字內容可以透過配置檔案自訂。編輯 `frontend/src/config/ui.config.js`：

```jsx
export const uiConfig = {
  appTitle: 'COOL RAG Assistant',
  headerTitle: 'COOL RAG Assistant',
  headerSubtitle: 'NTU COOL 文件智能問答助理',
  welcomeTitle: '👋 歡迎使用 COOL RAG Assistant',
  welcomeDescription: '我可以幫您回答關於 NTU COOL 的問題',
  exampleQuestions: [
    '如何在 NTU COOL 上建立課程？',
    'NTU COOL 有哪些功能？',
    '如何管理學生名單？',
  ],
  // ...更多設定
};
```

## **📁 專案結構**

```
cool-rag/
├── backend/                 # Backend API
│   ├── app/
│   │   ├── main.py         # FastAPI 應用入口
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 資料庫模型
│   │   ├── services/       # 業務邏輯
│   │   ├── api/            # API 路由
│   │   └── clients/        # 外部客戶端 (OpenAI)
│   ├── documents/          # 文件目錄 (放置 Markdown 文件)
│   │   └── .gitkeep
│   ├── uploaded_images/    # 上傳圖片目錄
│   │   └── .gitkeep
│   └── requirements.txt
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/    # React 組件
│   │   ├── apis/          # API 服務
│   │   └── config/        # 配置檔案
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## **🔧 進階設定**

### **調整檢索參數**

在 `.env` 檔案中：

```
TOP_K_RESULTS=5              # 檢索文件數量
SIMILARITY_THRESHOLD=0.7     # 相似度閾值 (0-1)
CHUNK_SIZE=800               # 文件分段大小
CHUNK_OVERLAP=150            # 段落重疊大小
```