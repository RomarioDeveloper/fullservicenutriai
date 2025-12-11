class Permission {
  constructor(id, categoryIndex, name, description = '') {
    this.id = id;
    this.categoryIndex = categoryIndex;
    this.name = name;
    this.description = description;
  }
}

class PermissionCategory {
  constructor(index, name, permissions = []) {
    this.index = index;
    this.name = name;
    this.permissions = permissions;
  }

  addPermission(permission) {
    if (!this.permissions.find(p => p.id === permission.id)) {
      this.permissions.push(permission);
    }
  }

  removePermission(permissionId) {
    this.permissions = this.permissions.filter(p => p.id !== permissionId);
  }

  getPermissionIndexes() {
    return this.permissions.map(p => p.id);
  }
}

module.exports = { Permission, PermissionCategory };

