| ID | Название | Описание | Метрика/Порог | Проверка (чем/где) | Компонент | Приор. |
|---|---|---|---|---|---|---|
| NFR-SEC-01 | Аутентификация JWT | Приватные эндпоинты доступны только с валидным JWT | 100% требуют JWT; `exp ≤ 3600s`; clock skew ≤ 60s | pytest e2e (401/403), BDD; проверка мидлвари | Auth / API Gateway | High |
| NFR-SEC-02 | Авторизация (RBAC + владелец) | Write/удаление только владельцем или `admin` | 0 успешных write от не-владельца без `admin` | ACL-тесты (pytest), BDD; ожидание 403 | API / Domain | High |
| NFR-SEC-03 | Хранение паролей | Нет хранения в открытом виде | `argon2id` (m≥65536, t≥3, p=1) **или** `bcrypt $2b$` (cost≥12) | Юнит-тест на префикс/параметры; статический анализ | Auth / Persistence | High |
| NFR-SEC-04 | Лимит логина | Защита от брутфорса на `/auth/login` | ≤10 неуспешных/мин на (IP, username); превышение → 429 | Интеграционный тест нагрузки; BDD; Redis-счётчик | API Middleware | High |
| NFR-SEC-05 | Глобальный rate limit | Квота по токену/пользователю | ≤120 req/мин на `sub`; превышение → 429 | Интеграционные тесты; метрики 429 | API Middleware | Medium |
| NFR-SEC-06 | Валидация и анти-инъекции | Жёсткие схемы; запрет сырого SQL | 100% публичных эндпоинтов валидируют вход; 0 конкатенаций SQL | Контракт-тесты 422; линтер/grep на raw SQL | API / ORM | High |
| NFR-SEC-07 | RFC7807 ошибки | Единый формат без PII | 100% 4xx/5xx → RFC7807; `X-Correlation-Id` в 100% ответов | Контракт-тесты; e2e; проверка маскирования | API | Medium |
| NFR-SEC-08 | Логи и аудит | Аудит без секретов | Логируются login/logout и CRUD Deck/Card; хранение ≥30 дней | Просмотр логов на stage; юнит на фильтр PII | Observability | Medium |
| NFR-SEC-09 | Уязвимости (SCA) | Быстрая фиксация High/Critical | Устранять ≤7 дней с момента детекта | CI: `pip-audit`/`safety`/SBOM; отчёт в PR | Build / CI | High |
| NFR-SEC-10 | Секреты | Нет секретов в коде; ротация | 0 секретов в репо; ротация ≥1 раз/30 дней | CI secret-scan (gitleaks/trufflehog); политика Vault/KMS | Platform / DevOps | Medium |
| NFR-SEC-11 | Транспорт | Только HTTPS в деплое | HSTS `max-age ≥ 31536000`; `Secure`/`HttpOnly`/`SameSite=Strict` для cookies | Smoke-тесты в staging (`curl -I`) | Ingress / Proxy | Medium |
| NFR-SEC-12 | CORS | Жёсткая allow-list политика | Разрешены только нужные origins/методы/заголовки; preflight только для них | e2e preflight; статический анализ конфигов | API Gateway | Low |
