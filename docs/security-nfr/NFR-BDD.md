Feature: JWT Authentication (NFR-SEC-01)
  Scenario: Access without token is denied
    Given a user exists and is not authenticated
    When the client calls GET /decks
    Then the response status should be 401

  Scenario: Expired token is rejected
    Given I have a JWT with exp in the past
    When I call GET /decks with this token
    Then the response status should be 401

Feature: Authorization owner/admin (NFR-SEC-02)
  Scenario: Non-owner cannot delete other's deck
    Given user A owns deck "French A1"
    And user B is authenticated but not admin
    When user B calls DELETE /decks/{deck_id}
    Then the response status should be 403

  Scenario: Admin can delete any deck
    Given user Admin with role "admin" is authenticated
    And a deck belongs to user A
    When Admin calls DELETE /decks/{deck_id}
    Then the response status should be 204

Feature: Brute-force protection on login (NFR-SEC-04)
  Scenario: Too many login attempts are throttled
    Given there were 10 failed logins for "u@example.com" from the same IP within 1 minute
    When another POST /auth/login with wrong password arrives
    Then the response status should be 429

Feature: Secure password storage (NFR-SEC-03)
  Scenario: Password is hashed with approved algorithm
    Given a user registers with password "Secret123!"
    When the password hash is stored
    Then it should start with "$argon2id$" or "$2b$"
    And parameters must meet the policy (argon2id m>=65536,t>=3,p=1 or bcrypt cost>=12)

Feature: RFC7807 error format without PII (NFR-SEC-07)
  Scenario: Error response masks secrets and contains correlation id
    Given an authenticated user
    When the client calls POST /cards with invalid payload
    Then the response status should be 422
    And response body should match RFC7807
    And response headers should contain "X-Correlation-Id"
    And response body should not contain fields "password", "token", "secret"
