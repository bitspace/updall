import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from utils.reporter import UpdateReporter


class TestUpdateReporter:
    """Test UpdateReporter functionality"""

    def test_init_with_logger(self, mock_logger):
        """Test UpdateReporter initialization with logger"""
        reporter = UpdateReporter(mock_logger)
        assert reporter.logger == mock_logger
        assert reporter.start_time is not None
        assert isinstance(reporter.start_time, datetime)

    def test_init_without_logger(self):
        """Test UpdateReporter initialization without logger"""
        reporter = UpdateReporter()
        assert reporter.logger is not None
        assert hasattr(reporter.logger, 'info')

    def test_add_system_result(self, mock_logger, sample_update_results):
        """Test adding system result"""
        reporter = UpdateReporter(mock_logger)
        
        reporter.add_system_result('test_laptop', sample_update_results)
        
        assert 'test_laptop' in reporter.system_results
        assert reporter.system_results['test_laptop'] == sample_update_results

    def test_calculate_summary_all_success(self, mock_logger):
        """Test calculating summary when all systems succeed"""
        reporter = UpdateReporter(mock_logger)
        
        # Add successful results for multiple systems
        reporter.add_system_result('laptop', {
            'rust': {'status': 'success', 'success': True},
            'node': {'status': 'success', 'success': True}
        })
        reporter.add_system_result('server', {
            'rust': {'status': 'success', 'success': True}
        })
        
        summary = reporter.calculate_summary()
        
        assert summary['total_systems'] == 2
        assert summary['successful_systems'] == 2
        assert summary['failed_systems'] == 0
        assert summary['total_update_types'] == 3
        assert summary['successful_updates'] == 3
        assert summary['failed_updates'] == 0

    def test_calculate_summary_with_failures(self, mock_logger):
        """Test calculating summary with some failures"""
        reporter = UpdateReporter(mock_logger)
        
        # Add mixed results
        reporter.add_system_result('laptop', {
            'rust': {'status': 'success', 'success': True},
            'node': {'status': 'failed', 'success': False}
        })
        reporter.add_system_result('server', {
            'rust': {'status': 'failed', 'success': False}
        })
        
        summary = reporter.calculate_summary()
        
        assert summary['total_systems'] == 2
        assert summary['successful_systems'] == 0  # No system fully succeeded
        assert summary['failed_systems'] == 2
        assert summary['total_update_types'] == 3
        assert summary['successful_updates'] == 1
        assert summary['failed_updates'] == 2

    def test_calculate_summary_empty_results(self, mock_logger):
        """Test calculating summary with no results"""
        reporter = UpdateReporter(mock_logger)
        
        summary = reporter.calculate_summary()
        
        assert summary['total_systems'] == 0
        assert summary['successful_systems'] == 0
        assert summary['failed_systems'] == 0
        assert summary['total_update_types'] == 0
        assert summary['successful_updates'] == 0
        assert summary['failed_updates'] == 0

    def test_generate_summary_report(self, mock_logger):
        """Test generating summary report"""
        reporter = UpdateReporter(mock_logger)
        
        # Add test data
        reporter.add_system_result('laptop', {
            'rust': {
                'status': 'success',
                'success': True,
                'commands': [{'command': 'rustup update', 'duration': 1.5}]
            }
        })
        
        # Mock end time to be 5 minutes after start
        reporter.end_time = reporter.start_time + timedelta(minutes=5)
        
        report = reporter.generate_summary_report()
        
        assert '=== System Update Report ===' in report
        assert 'laptop' in report
        assert 'rust' in report
        assert 'Total duration: 5m 0s' in report
        assert '✓' in report  # Success indicator

    def test_generate_summary_report_with_failures(self, mock_logger):
        """Test generating summary report with failures"""
        reporter = UpdateReporter(mock_logger)
        
        # Add failed update
        reporter.add_system_result('server', {
            'rust': {
                'status': 'failed',
                'success': False,
                'error': 'Command failed with exit code 1'
            }
        })
        
        report = reporter.generate_summary_report()
        
        assert 'server' in report
        assert 'rust' in report
        assert '✗' in report  # Failure indicator
        assert 'Command failed' in report

    def test_generate_json_report(self, mock_logger):
        """Test generating JSON report"""
        reporter = UpdateReporter(mock_logger)
        
        # Add test data
        reporter.add_system_result('laptop', {
            'rust': {'status': 'success', 'success': True}
        })
        
        # Mock end time
        reporter.end_time = reporter.start_time + timedelta(minutes=3)
        
        json_report = reporter.generate_json_report()
        
        # Parse JSON to verify structure
        report_data = json.loads(json_report)
        
        assert 'metadata' in report_data
        assert 'summary' in report_data
        assert 'systems' in report_data
        assert report_data['metadata']['total_duration'] == 180.0  # 3 minutes in seconds
        assert 'laptop' in report_data['systems']

    def test_save_report_to_file(self, mock_logger):
        """Test saving report to file"""
        reporter = UpdateReporter(mock_logger)
        
        # Add test data
        reporter.add_system_result('laptop', {
            'rust': {'status': 'success', 'success': True}
        })
        
        # Test saving summary report
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name
        
        try:
            reporter.save_report_to_file(temp_path, format='summary')
            
            # Verify file was created and contains expected content
            with open(temp_path, 'r') as f:
                content = f.read()
            
            assert '=== System Update Report ===' in content
            assert 'laptop' in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_save_json_report_to_file(self, mock_logger):
        """Test saving JSON report to file"""
        reporter = UpdateReporter(mock_logger)
        
        # Add test data
        reporter.add_system_result('laptop', {
            'rust': {'status': 'success', 'success': True}
        })
        
        # Test saving JSON report
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            reporter.save_report_to_file(temp_path, format='json')
            
            # Verify file was created and contains valid JSON
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert 'metadata' in data
            assert 'systems' in data
            assert 'laptop' in data['systems']
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_save_report_invalid_format(self, mock_logger):
        """Test saving report with invalid format"""
        reporter = UpdateReporter(mock_logger)
        
        with pytest.raises(ValueError, match="Unsupported report format"):
            reporter.save_report_to_file('/tmp/test.txt', format='invalid')

    def test_format_duration_seconds(self, mock_logger):
        """Test formatting duration in seconds"""
        reporter = UpdateReporter(mock_logger)
        
        # Test various durations
        assert reporter.format_duration(45.5) == "45s"
        assert reporter.format_duration(1.2) == "1s"

    def test_format_duration_minutes(self, mock_logger):
        """Test formatting duration in minutes"""
        reporter = UpdateReporter(mock_logger)
        
        assert reporter.format_duration(65.0) == "1m 5s"
        assert reporter.format_duration(125.7) == "2m 5s"

    def test_format_duration_hours(self, mock_logger):
        """Test formatting duration in hours"""
        reporter = UpdateReporter(mock_logger)
        
        assert reporter.format_duration(3665.0) == "1h 1m 5s"
        assert reporter.format_duration(7320.0) == "2h 2m 0s"

    def test_format_duration_zero(self, mock_logger):
        """Test formatting zero duration"""
        reporter = UpdateReporter(mock_logger)
        
        assert reporter.format_duration(0.0) == "0s"
        assert reporter.format_duration(0.1) == "0s"

    def test_get_status_icon_success(self, mock_logger):
        """Test getting status icon for successful update"""
        reporter = UpdateReporter(mock_logger)
        
        icon = reporter.get_status_icon(True)
        assert icon == "✓"

    def test_get_status_icon_failure(self, mock_logger):
        """Test getting status icon for failed update"""
        reporter = UpdateReporter(mock_logger)
        
        icon = reporter.get_status_icon(False)
        assert icon == "✗"

    def test_calculate_total_duration(self, mock_logger):
        """Test calculating total duration"""
        reporter = UpdateReporter(mock_logger)
        
        # Set end time to 10 minutes after start
        reporter.end_time = reporter.start_time + timedelta(minutes=10)
        
        duration = reporter.calculate_total_duration()
        assert duration == 600.0  # 10 minutes in seconds

    def test_calculate_total_duration_no_end_time(self, mock_logger):
        """Test calculating total duration when end time is not set"""
        reporter = UpdateReporter(mock_logger)
        
        # Don't set end_time, should use current time
        with patch('utils.reporter.datetime') as mock_datetime:
            mock_now = reporter.start_time + timedelta(minutes=5)
            mock_datetime.now.return_value = mock_now
            
            duration = reporter.calculate_total_duration()
            assert duration == 300.0  # 5 minutes in seconds

    def test_mark_complete(self, mock_logger):
        """Test marking report as complete"""
        reporter = UpdateReporter(mock_logger)
        
        # End time should not be set initially
        assert reporter.end_time is None
        
        reporter.mark_complete()
        
        # End time should now be set
        assert reporter.end_time is not None
        assert isinstance(reporter.end_time, datetime)

    def test_generate_report_with_command_details(self, mock_logger, sample_command_results):
        """Test generating report with detailed command information"""
        reporter = UpdateReporter(mock_logger)
        
        # Add system with detailed command results
        reporter.add_system_result('laptop', {
            'rust': {
                'status': 'success',
                'success': True,
                'commands': sample_command_results
            }
        })
        
        report = reporter.generate_summary_report()
        
        # Should include command details
        assert 'rustup update' in report
        assert 'cargo install-update' in report
        assert '1.5' in report  # Duration from first command
        assert '2.3' in report  # Duration from second command

    def test_generate_report_with_error_details(self, mock_logger):
        """Test generating report with error details"""
        reporter = UpdateReporter(mock_logger)
        
        # Add system with error
        reporter.add_system_result('server', {
            'node': {
                'status': 'failed',
                'success': False,
                'error': 'npm command not found',
                'commands': [{
                    'command': 'npm update -g',
                    'exit_code': 127,
                    'stderr': 'npm: command not found',
                    'success': False
                }]
            }
        })
        
        report = reporter.generate_summary_report()
        
        # Should include error information
        assert 'npm command not found' in report
        assert 'exit code 127' in report or '127' in report

    def test_complex_multi_system_report(self, mock_logger):
        """Test generating complex report with multiple systems and mixed results"""
        reporter = UpdateReporter(mock_logger)
        
        # Add multiple systems with various results
        reporter.add_system_result('laptop', {
            'rust': {'status': 'success', 'success': True},
            'node': {'status': 'success', 'success': True},
            'gcloud': {'status': 'success', 'success': True}
        })
        
        reporter.add_system_result('server', {
            'rust': {'status': 'success', 'success': True},
            'node': {'status': 'failed', 'success': False, 'error': 'Network timeout'}
        })
        
        reporter.add_system_result('vps', {
            'rust': {'status': 'failed', 'success': False, 'error': 'rustup not installed'}
        })
        
        summary = reporter.calculate_summary()
        report = reporter.generate_summary_report()
        
        # Verify summary calculations
        assert summary['total_systems'] == 3
        assert summary['successful_systems'] == 1  # Only laptop fully succeeded
        assert summary['failed_systems'] == 2
        assert summary['total_update_types'] == 6
        assert summary['successful_updates'] == 4
        assert summary['failed_updates'] == 2
        
        # Verify report content
        assert 'laptop' in report
        assert 'server' in report
        assert 'vps' in report
        assert 'Network timeout' in report
        assert 'rustup not installed' in report