def test_find_packages_with_symlinks(tmp_path):
    """Test package discovery with symbolic links"""
    real_pkg = tmp_path / "real_pkg"
    real_pkg.mkdir()
    (real_pkg / "__init__.py").touch()
    
    symlink_pkg = tmp_path / "symlink_pkg"
    symlink_pkg.symlink_to(real_pkg)
    
    config = chewedConfig()
    packages = find_python_packages(symlink_pkg, config)
    assert len(packages) == 1
    assert packages[0]["path"] == str(real_pkg.resolve()) 