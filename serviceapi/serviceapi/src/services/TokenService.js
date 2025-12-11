const Token = require('../models/Token');

const tokensStorage = new Map();

class TokenService {
  static getToken(tokenValue) {
    return tokensStorage.get(tokenValue) || null;
  }

  static setToken(tokenValue, categories, indexes, permissionsValues) {
    const token = new Token(tokenValue, categories, indexes, permissionsValues);
    tokensStorage.set(tokenValue, token);
    return token;
  }

  static isValidToken(tokenValue) {
    return tokensStorage.has(tokenValue);
  }

  static getTokenPermissions(tokenValue) {
    const token = tokensStorage.get(tokenValue);
    if (!token) {
      return null;
    }
    return {
      categories: token.categories,
      indexes: token.indexes,
      permissionsValues: token.permissionsValues
    };
  }
}

module.exports = TokenService;

