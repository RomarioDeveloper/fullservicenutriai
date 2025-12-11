class User {
  constructor(id, categories = [], indexes = [], permissionsValues = []) {
    this.id = id;
    this.categories = categories;
    this.indexes = indexes;
    this.permissionsValues = permissionsValues;
  }

  hasPermission(categoryIndex, permissionIndex) {
    if (!this.categories.includes(categoryIndex)) {
      return false;
    }
    return this.permissionsValues.includes(permissionIndex);
  }

  getPermissionsForCategory(categoryIndex) {
    if (!this.categories.includes(categoryIndex)) {
      return [];
    }
    return this.permissionsValues;
  }
}

module.exports = User;

