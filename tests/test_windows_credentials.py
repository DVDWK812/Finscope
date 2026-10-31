"""Exercise Windows marshalling with mocked native calls on every CI platform."""
import ctypes as c
import unittest
from unittest.mock import Mock
from finscope.windows_credentials import Credential, Win32CredentialBindings


class WindowsAdapterTests(unittest.TestCase):
    def setUp(self):
        self.api = Mock()
        self.bindings = Win32CredentialBindings(self.api)

    def test_write_uses_exact_provider_target_utf16_and_user_persistence(self):
        captured = {}
        def write(pointer, flags):
            value = c.cast(pointer,c.POINTER(Credential)).contents
            captured.update(target=value.TargetName,user=value.UserName,type=value.Type,persist=value.Persist,
                text=c.string_at(value.CredentialBlob,value.CredentialBlobSize).decode('utf-16-le'),flags=flags)
            return True
        self.api.CredWriteW.side_effect = write
        self.bindings.write('deepseek','AUTHORED-密钥')
        self.assertEqual(captured,{'target':'FinScope local / deepseek','user':'deepseek','type':1,'persist':2,'text':'AUTHORED-密钥','flags':0})
        self.api.CredReadW.assert_not_called(); self.api.CredDeleteW.assert_not_called()

    def test_read_returns_utf16_and_frees_only_the_mock_allocated_pointer(self):
        text = 'AUTHORED-WINDOWS-ONLY'
        blob = (c.c_ubyte*len(text.encode('utf-16-le'))).from_buffer_copy(text.encode('utf-16-le'))
        entry = Credential(); entry.CredentialBlobSize=len(blob); entry.CredentialBlob=c.cast(blob,c.POINTER(c.c_ubyte))
        def read(target,kind,flags,pointer):
            self.assertEqual((target,kind,flags),('FinScope local / marketaux',1,0))
            c.cast(pointer,c.POINTER(c.POINTER(Credential)))[0] = c.pointer(entry)
            return True
        self.api.CredReadW.side_effect = read
        self.assertEqual(self.bindings.read('marketaux'),text)
        self.api.CredFree.assert_called_once(); self.api.CredWriteW.assert_not_called()

    def test_missing_read_does_not_free_or_write_and_failed_write_is_redacted(self):
        self.api.CredReadW.return_value = False
        self.assertEqual(self.bindings.read('finnhub'),''); self.api.CredFree.assert_not_called()
        self.api.CredWriteW.return_value = False
        with self.assertRaises(ValueError) as error:self.bindings.write('marketaux','AUTHORED-NOT-IN-ERROR')
        self.assertNotIn('AUTHORED-NOT-IN-ERROR',str(error.exception));self.api.CredDeleteW.assert_not_called()

    def test_invalid_provider_or_value_rejected_before_mock_native_calls(self):
        for provider,value in (('unsupported','AUTHORED'),('marketaux',''),('marketaux',' '*10)):
            with self.assertRaises(ValueError):self.bindings.write(provider,value)
        self.api.CredWriteW.assert_not_called();self.api.CredReadW.assert_not_called()

    def test_mocked_native_exceptions_never_echo_secret_in_errors(self):
        for name,action in (('CredReadW',lambda:self.bindings.read('marketaux')),
                            ('CredWriteW',lambda:self.bindings.write('marketaux','AUTHORED-ERROR-KEY'))):
            getattr(self.api,name).side_effect=OSError('AUTHORED-ERROR-KEY')
            with self.assertRaises(ValueError) as error:action()
            self.assertNotIn('AUTHORED-ERROR-KEY',str(error.exception))

    def test_malformed_utf16_is_redacted_and_mock_allocation_still_freed(self):
        blob=(c.c_ubyte*1)(255);entry=Credential();entry.CredentialBlobSize=1
        entry.CredentialBlob=c.cast(blob,c.POINTER(c.c_ubyte))
        def read(target,kind,flags,pointer):
            c.cast(pointer,c.POINTER(c.POINTER(Credential)))[0]=c.pointer(entry);return True
        self.api.CredReadW.side_effect=read
        with self.assertRaisesRegex(ValueError,'Windows credential read failed'):self.bindings.read('marketaux')
        self.api.CredFree.assert_called_once()


if __name__ == '__main__':unittest.main()
