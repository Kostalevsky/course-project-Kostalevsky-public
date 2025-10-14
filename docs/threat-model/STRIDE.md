| Поток/Элемент | Угроза (STRIDE) | Риск | Контроль | Ссылка на NFR | Проверка/Артефакт |
|----------------|------------------|------|-----------|----------------|--------------------|
| F1 /login | S: Spoofing (подмена пользователя) | R1 | JWT + rate-limit + MFA (опционально) | NFR-SEC-01, NFR-SEC-04 | e2e + ZAP baseline |
| F2 Auth validation | T: Tampering (подмена токена) | R2 | Проверка подписи JWT, exp, aud | NFR-SEC-01 | unit-тесты auth |
| F3 DB query (user) | R: Repudiation | R3 | Логирование успешных/неуспешных логинов | NFR-SEC-06 | audit logs |
| F4 CRUD decks/cards | I: Information Disclosure | R4 | Role-based access (только владелец) | NFR-SEC-03 | pytest test_auth |
| F5 Write deck | D: Denial of Service | R5 | Rate limiting, input validation | NFR-SEC-04 | k6 / pytest |
| F6 Error messages | I: Information Disclosure | R6 | RFC7807 + скрытие stack traces | NFR-SEC-02 | контрактные тесты |
| F7 Metrics | E: Elevation of Privilege | R7 | Только для админов / API key | NFR-SEC-05 | postman + CI scan |
| F8 Logs | T: Tampering | R8 | Write-only audit trail | NFR-SEC-06 | лог-ревью |
