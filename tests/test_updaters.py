import pytest
from unittest.mock import Mock, patch, mock_open
import subprocess
import json

from updaters.rust import RustUpdater
from updaters.node import NodeUpdater
from updaters.sdkman import SdkmanUpdater
from updaters.gcloud import GcloudUpdater
from updaters.package_manager import PackageManagerUpdater


class TestRustUpdater:
    """Test Rust updater functionality"""

    def test_get_update_commands(self):
        """Test getting Rust update commands"""
        commands = RustUpdater.get_update_commands()
        
        assert len(commands) == 2
        assert commands[0][0] == 'rustup update'
        assert commands[1][0] == 'cargo install-update -a'
        
        # All commands should not need sudo
        for cmd, opts in commands:
            assert opts['needs_sudo'] is False

    @patch('subprocess.run')
    def test_check_availability_available(self, mock_run):
        """Test check_availability when rustup is available"""
        mock_run.return_value.returncode = 0
        
        result = RustUpdater.check_availability()
        assert result is True
        mock_run.assert_called_once_with(['rustup', '--version'], capture_output=True, check=True)

    @patch('subprocess.run')
    def test_check_availability_not_available(self, mock_run):
        """Test check_availability when rustup is not available"""
        mock_run.side_effect = FileNotFoundError()
        
        result = RustUpdater.check_availability()
        assert result is False

    @patch('subprocess.run')
    def test_get_version_info_success(self, mock_run):
        """Test getting Rust version info successfully"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "rustc 1.70.0 (90c541806 2023-05-31)"
        
        version = RustUpdater.get_version_info()
        assert version == "rustc 1.70.0 (90c541806 2023-05-31)"

    @patch('subprocess.run')
    def test_get_version_info_failure(self, mock_run):
        """Test getting Rust version info when command fails"""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'rustc')
        
        version = RustUpdater.get_version_info()
        assert version is None

    def test_parse_update_output_with_updates(self):
        """Test parsing rustup output with updates"""
        output = """
info: syncing channel updates for 'stable-x86_64-unknown-linux-gnu'
info: latest update on 2023-05-31, rust version 1.70.0
updated 2 components

rustc 1.70.0 (90c541806 2023-05-31)
"""
        
        info = RustUpdater.parse_update_output(output)
        assert len(info['updated_components']) > 0
        assert info['already_up_to_date'] is False
        assert info['version'] == "rustc 1.70.0 (90c541806 2023-05-31)"

    def test_parse_update_output_up_to_date(self):
        """Test parsing rustup output when up to date"""
        output = """
info: checking for self-update
info: component 'rustc' is up to date
"""
        
        info = RustUpdater.parse_update_output(output)
        assert info['already_up_to_date'] is True
        assert len(info['updated_components']) == 0


class TestNodeUpdater:
    """Test Node.js updater functionality"""

    def test_get_update_commands(self):
        """Test getting Node.js update commands"""
        commands = NodeUpdater.get_update_commands()
        
        assert len(commands) == 1
        assert commands[0][0] == 'npm update -g'
        assert commands[0][1]['needs_sudo'] is False

    @patch('subprocess.run')
    def test_check_availability_available(self, mock_run):
        """Test check_availability when npm is available"""
        mock_run.return_value.returncode = 0
        
        result = NodeUpdater.check_availability()
        assert result is True

    @patch('subprocess.run')
    def test_check_availability_not_available(self, mock_run):
        """Test check_availability when npm is not available"""
        mock_run.side_effect = FileNotFoundError()
        
        result = NodeUpdater.check_availability()
        assert result is False

    @patch('subprocess.run')
    def test_get_version_info_success(self, mock_run):
        """Test getting Node.js version info successfully"""
        mock_run.side_effect = [
            Mock(returncode=0, stdout="v18.16.0"),  # node --version
            Mock(returncode=0, stdout="9.5.1")      # npm --version
        ]
        
        versions = NodeUpdater.get_version_info()
        assert versions['node'] == "v18.16.0"
        assert versions['npm'] == "9.5.1"

    @patch('subprocess.run')
    def test_get_outdated_packages_with_packages(self, mock_run):
        """Test getting outdated packages when some exist"""
        outdated_json = {
            "package1": {"current": "1.0.0", "wanted": "1.1.0"},
            "package2": {"current": "2.0.0", "wanted": "2.1.0"}
        }
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(outdated_json)
        
        packages = NodeUpdater.get_outdated_packages()
        assert len(packages) == 2
        assert "package1" in packages
        assert "package2" in packages

    @patch('subprocess.run')
    def test_get_outdated_packages_none(self, mock_run):
        """Test getting outdated packages when none exist"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        
        packages = NodeUpdater.get_outdated_packages()
        assert len(packages) == 0

    def test_parse_update_output_with_updates(self):
        """Test parsing npm update output with updates"""
        output = """
+ package1@1.1.0
+ package2@2.1.0
updated 2 packages in 5.234s
"""
        
        info = NodeUpdater.parse_update_output(output)
        assert len(info['updated_packages']) >= 2
        assert info['already_up_to_date'] is False

    def test_parse_update_output_up_to_date(self):
        """Test parsing npm update output when up to date"""
        output = "up to date, audited 150 packages in 1.234s"
        
        info = NodeUpdater.parse_update_output(output)
        assert info['already_up_to_date'] is True


class TestSdkmanUpdater:
    """Test SDKman updater functionality"""

    def test_get_update_commands(self):
        """Test getting SDKman update commands"""
        commands = SdkmanUpdater.get_update_commands()
        
        assert len(commands) == 3
        expected_commands = ['sdk selfupdate', 'sdk update', 'sdk upgrade']
        
        for i, (cmd, opts) in enumerate(commands):
            assert cmd == expected_commands[i]
            assert opts['needs_sudo'] is False

    @patch('os.path.exists')
    def test_check_availability_available(self, mock_exists):
        """Test check_availability when SDKman is available"""
        mock_exists.return_value = True
        
        result = SdkmanUpdater.check_availability()
        assert result is True

    @patch('os.path.exists')
    def test_check_availability_not_available(self, mock_exists):
        """Test check_availability when SDKman is not available"""
        mock_exists.return_value = False
        
        result = SdkmanUpdater.check_availability()
        assert result is False

    @patch('subprocess.run')
    def test_get_version_info_success(self, mock_run):
        """Test getting SDKman version info successfully"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "SDKMAN 5.18.0"
        
        version = SdkmanUpdater.get_version_info()
        assert version == "SDKMAN 5.18.0"

    def test_parse_update_output_selfupdate_success(self):
        """Test parsing SDKman selfupdate output"""
        output = "Successfully updated SDKMAN to version 5.18.1"
        
        info = SdkmanUpdater.parse_update_output(output)
        assert info['selfupdate_success'] is True

    def test_parse_update_output_upgrade_available(self):
        """Test parsing SDKman output with upgrade available"""
        output = """
Java 17.0.7-oracle upgrade available
Kotlin 1.8.22 upgrade available
"""
        
        info = SdkmanUpdater.parse_update_output(output)
        assert len(info['upgrades_available']) >= 2


class TestGcloudUpdater:
    """Test Google Cloud SDK updater functionality"""

    def test_get_update_commands(self):
        """Test getting gcloud update commands"""
        commands = GcloudUpdater.get_update_commands()
        
        assert len(commands) == 1
        assert commands[0][0] == 'gcloud components update --quiet'
        assert commands[0][1]['needs_sudo'] is False

    @patch('subprocess.run')
    def test_check_availability_available(self, mock_run):
        """Test check_availability when gcloud is available"""
        mock_run.return_value.returncode = 0
        
        result = GcloudUpdater.check_availability()
        assert result is True

    @patch('subprocess.run')
    def test_check_availability_not_available(self, mock_run):
        """Test check_availability when gcloud is not available"""
        mock_run.side_effect = FileNotFoundError()
        
        result = GcloudUpdater.check_availability()
        assert result is False

    @patch('subprocess.run')
    def test_get_version_info_success(self, mock_run):
        """Test getting gcloud version info successfully"""
        output = """Google Cloud SDK 432.0.0
bq 2.0.91
gsutil 5.23
gcloud 432.0.0"""
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = output
        
        versions = GcloudUpdater.get_version_info()
        assert 'sdk' in versions
        assert 'bq' in versions
        assert 'gsutil' in versions
        assert 'gcloud' in versions

    @patch('subprocess.run')
    def test_get_installed_components_success(self, mock_run):
        """Test getting installed components successfully"""
        output = """
COMPONENT NAME    STATUS
├─ BigQuery Command Line Tool    Installed
├─ Cloud Storage Command Line Tool    Installed
├─ gcloud cli (Platform Specific)    Installed
"""
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = output
        
        components = GcloudUpdater.get_installed_components()
        assert len(components) >= 2  # Should find components marked as Installed

    def test_parse_update_output_with_updates(self):
        """Test parsing gcloud update output with updates"""
        output = """
The following components will be updated:
  Component 'gcloud' will be updated to version 432.0.0
  Component 'bq' will be updated to version 2.0.92

Updated component 'gcloud' to version 432.0.0
Updated component 'bq' to version 2.0.92
"""
        
        info = GcloudUpdater.parse_update_output(output)
        assert len(info['updated_components']) >= 2
        assert info['already_up_to_date'] is False

    def test_parse_update_output_up_to_date(self):
        """Test parsing gcloud output when up to date"""
        output = "All components are up to date."
        
        info = GcloudUpdater.parse_update_output(output)
        assert info['already_up_to_date'] is True


class TestPackageManagerUpdater:
    """Test PackageManagerUpdater functionality"""

    def test_parse_paru_output_with_updates(self):
        """Test parsing paru output with package updates"""
        output = """
:: Synchronizing package databases...
 core                     164.2 KiB   890 KiB/s 00:00
 extra                   1652.5 KiB  1234 KiB/s 00:01
 community                  6.9 MiB  2.12 MiB/s 00:03

package1 1.0.0-1 -> 1.1.0-1
package2 2.0.0-1 -> 2.1.0-1

Total Download Size:   45.67 MiB
"""
        
        info = PackageManagerUpdater.parse_paru_output(output)
        assert info['total_packages'] >= 2
        assert info['total_download_size'] == "45.67 MiB"
        assert info['already_up_to_date'] is False

    def test_parse_paru_output_up_to_date(self):
        """Test parsing paru output when system is up to date"""
        output = """
:: Synchronizing package databases...
 there is nothing to do
"""
        
        info = PackageManagerUpdater.parse_paru_output(output)
        assert info['already_up_to_date'] is True
        assert info['total_packages'] == 0

    def test_parse_apt_output_with_updates(self):
        """Test parsing apt output with package updates"""
        output = """
Reading package lists...
Building dependency tree...
5 upgraded, 2 newly installed, 1 to remove and 0 not upgraded.
Need to get 42.3 MB of archives.
Get:1 http://archive.ubuntu.com/ubuntu focal/main package1 [1.2 MB]
Get:2 http://archive.ubuntu.com/ubuntu focal/main package2 [2.3 MB]
"""
        
        info = PackageManagerUpdater.parse_apt_output(output)
        assert info['total_packages'] == 5
        assert len(info['packages_updated']) >= 2
        assert "Need to get" in info['download_size']

    def test_parse_apt_output_up_to_date(self):
        """Test parsing apt output when system is up to date"""
        output = """
Reading package lists...
Building dependency tree...
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
"""
        
        info = PackageManagerUpdater.parse_apt_output(output)
        assert info['already_up_to_date'] is True
        assert info['total_packages'] == 0

    @patch('builtins.open', new_callable=mock_open, read_data='PRETTY_NAME="Ubuntu 20.04.6 LTS"')
    @patch('subprocess.run')
    def test_get_system_info_success(self, mock_run, mock_file):
        """Test getting system information successfully"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "test-hostname"
        
        info = PackageManagerUpdater.get_system_info()
        assert info['os'] == "Ubuntu 20.04.6 LTS"
        assert info['hostname'] == "test-hostname"

    @patch('builtins.open', side_effect=FileNotFoundError())
    @patch('subprocess.run')
    def test_get_system_info_no_os_release(self, mock_run, mock_file):
        """Test getting system info when os-release file is missing"""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'hostname')
        
        info = PackageManagerUpdater.get_system_info()
        assert info['os'] == "Unknown"
        assert info['hostname'] == "Unknown"