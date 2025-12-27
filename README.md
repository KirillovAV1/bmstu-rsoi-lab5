# Лабораторная работа #5

## OAuth2 Authorization

### Формулировка

На базе [Лабораторной работы #4](https://github.com/KirillovAV1/bmstu-rsoi-lab4) реализована OAuth2 token-based
авторизация.

* Для авторизации используется OpenID Connect, в роли Identity Provider Auth0.
* На Identity Provider используется Resource Owner Password flow.
* Все методы `/api/**` (кроме `/api/v1/authorize` и `/manage/health)) на всех сервисах закрыть token-based
  авторизацией.
* В качестве токена используется JWT, для валидации токена JWKs.
* JWT токен пробрасывается между сервисами, при получении запроса валидацию токена так же реализована через JWKs.
* Убран заголовок `X-User-Name`. Пользователя получаем из JWT-токена.
* Если авторизация некорректная (отсутствие токена, ошибка валидации JWT токена, закончилось время жизни токена
  (поле `exp` в payload)), то отдается 401 ошибка.
* В `scope` указана `openid profile email`.
