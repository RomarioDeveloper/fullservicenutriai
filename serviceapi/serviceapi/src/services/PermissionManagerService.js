const TokenService = require('./TokenService');
const UserService = require('./UserService');
const PermissionService = require('./PermissionService');

class PermissionManagerService {
  static getCategoryLists(categories, indexes) {
    if (!categories || categories.length === 0) {
      return PermissionService.getAllCategories().map(cat => cat.index);
    }
    return categories;
  }

  static getAllowedPermissions(tokenValue, categories, indexes) {
    const token = TokenService.getToken(tokenValue);
    if (!token) {
      return [];
    }

    const tokenPermissions = new Set();
    categories.forEach(categoryIndex => {
      const perms = token.getPermissionsForCategory(categoryIndex);
      perms.forEach(perm => tokenPermissions.add(perm));
    });

    const availablePermissions = PermissionService.getAvailablePermissionsForCategories(categories);

    return availablePermissions.filter(perm => tokenPermissions.has(perm));
  }

  static async getFilteredUsers(categories, indexes) {
    return await UserService.getUsersByFilters(categories, indexes);
  }

  static async setPermissions(tokenValue, categories, indexes, permissionsValues) {
    const users = await this.getFilteredUsers(categories, indexes);
    
    if (users.length === 0) {
      return {
        allowedPermissions: this.getAllowedPermissions(tokenValue, categories, indexes),
        message: 'Список пользователей пуст. Возвращены все допустимые права для выдачи и отнятия исходя из прав токена.'
      };
    }

    const results = [];
    for (const user of users) {
      const allowedPerms = this.getAllowedPermissions(tokenValue, categories, indexes);
      const validPermissions = permissionsValues.filter(perm => allowedPerms.includes(perm));

      await UserService.setUser(user.id, categories, indexes, validPermissions);
      results.push({
        userId: user.id,
        permissions: validPermissions
      });
    }

    return {
      success: true,
      affectedUsers: results.length,
      results
    };
  }

  static async addPermissions(tokenValue, categories, indexes, permissionsValues) {
    const users = await this.getFilteredUsers(categories, indexes);
    
    if (users.length === 0) {
      return {
        allowedPermissions: this.getAllowedPermissions(tokenValue, categories, indexes),
        message: 'Список пользователей пуст. Возвращены все допустимые права для выдачи и отнятия исходя из прав токена.'
      };
    }

    const results = [];
    for (const user of users) {
      const currentPerms = new Set(user.permissionsValues || []);
      const allowedPerms = this.getAllowedPermissions(tokenValue, categories, indexes);
      
      permissionsValues.forEach(perm => {
        if (allowedPerms.includes(perm)) {
          currentPerms.add(perm);
        }
      });

      const newPermissions = Array.from(currentPerms);
      await UserService.setUser(user.id, categories, indexes, newPermissions);
      results.push({
        userId: user.id,
        permissions: newPermissions
      });
    }

    return {
      success: true,
      affectedUsers: results.length,
      results
    };
  }

  static async removePermissions(tokenValue, categories, indexes, permissionsValues) {
    const users = await this.getFilteredUsers(categories, indexes);
    
    if (users.length === 0) {
      return {
        allowedPermissions: this.getAllowedPermissions(tokenValue, categories, indexes),
        message: 'Список пользователей пуст. Возвращены все допустимые права для выдачи и отнятия исходя из прав токена.'
      };
    }

    const results = [];
    for (const user of users) {
      const currentPerms = user.permissionsValues || [];
      const allowedPerms = this.getAllowedPermissions(tokenValue, categories, indexes);
      
      const permissionsToRemove = permissionsValues.filter(perm => allowedPerms.includes(perm));
      const newPermissions = currentPerms.filter(perm => !permissionsToRemove.includes(perm));

      await UserService.setUser(user.id, categories, indexes, newPermissions);
      results.push({
        userId: user.id,
        permissions: newPermissions
      });
    }

    return {
      success: true,
      affectedUsers: results.length,
      results
    };
  }

  static async listPermissions(tokenValue, categories, indexes) {
    const users = await this.getFilteredUsers(categories, indexes);
    
    if (users.length === 0) {
      return {
        allowedPermissions: this.getAllowedPermissions(tokenValue, categories, indexes),
        message: 'Список пользователей пуст. Возвращены все допустимые права для выдачи и отнятия исходя из прав токена.'
      };
    }

    const results = [];
    for (const user of users) {
      results.push({
        userId: user.id,
        categories: user.categories,
        indexes: user.indexes,
        permissions: user.permissionsValues || []
      });
    }

    return {
      success: true,
      users: results
    };
  }
}

module.exports = PermissionManagerService;
