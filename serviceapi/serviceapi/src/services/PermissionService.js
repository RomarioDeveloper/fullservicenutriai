const { PermissionCategory } = require('../models/Permission');

const categoriesStorage = new Map();

class PermissionService {
  static getCategory(categoryIndex) {
    return categoriesStorage.get(categoryIndex) || null;
  }

  static createCategory(index, name, permissions = []) {
    const category = new PermissionCategory(index, name, permissions);
    categoriesStorage.set(index, category);
    return category;
  }

  static getAllCategories() {
    return Array.from(categoriesStorage.values());
  }

  static getAvailablePermissionsForCategory(categoryIndex) {
    const category = categoriesStorage.get(categoryIndex);
    if (!category) {
      return [];
    }
    return category.getPermissionIndexes();
  }

  static getAvailablePermissionsForCategories(categoryIndexes) {
    const allPermissions = new Set();
    
    categoryIndexes.forEach(categoryIndex => {
      const permissions = this.getAvailablePermissionsForCategory(categoryIndex);
      permissions.forEach(perm => allPermissions.add(perm));
    });

    return Array.from(allPermissions);
  }

  static isValidPermission(categoryIndex, permissionIndex) {
    const category = categoriesStorage.get(categoryIndex);
    if (!category) {
      return false;
    }
    return category.permissions.some(p => p.id === permissionIndex);
  }
}

module.exports = PermissionService;

