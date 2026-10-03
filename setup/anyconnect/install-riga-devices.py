"""Install Riga personal enforcement; UK activates this node separately."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

PAYLOAD = {'riga-devices.py': {'sha256': '3b50778a24b8c3ac73ac167fda494d0d90c85ba5dd85cecc2cbccf55bf3d12b1', 'data': 'IyEvdXNyL2Jpbi9weXRob24zCiIiIlJpZ2EgZGF0YS1wbGFuZSBkZXZpY2UgcmVnaXN0cnkuIE5vIGFjY291bnRzLCBzaWduaW5nIGtleXMgb3IgY2VydGlmaWNhdGVzLiIiIgpmcm9tIGNvbnRleHRsaWIgaW1wb3J0IGNvbnRleHRtYW5hZ2VyCmltcG9ydCBmY250bAppbXBvcnQgaGFzaGxpYgppbXBvcnQgaXBhZGRyZXNzCmltcG9ydCBqc29uCmltcG9ydCBvcwpmcm9tIHBhdGhsaWIgaW1wb3J0IFBhdGgKaW1wb3J0IHJlCmltcG9ydCBzaHV0aWwKaW1wb3J0IHN1YnByb2Nlc3MKaW1wb3J0IHN5cwppbXBvcnQgdGVtcGZpbGUKaW1wb3J0IHRpbWUKCkRJUkVDVE9SWSA9IFBhdGgoJy9ldGMvb2NzZXJ2L3RvbGYtdWsnKQpSVU5USU1FID0gUGF0aCgnL3J1bi90b2xmLW9jLXJpZ2EtZGV2aWNlcycpClBST0ZJTEVTID0gUGF0aCgnL2V0Yy9vY3NlcnYvdG9sZi1kZXZpY2UtY29uZmlnJykKQ09ORiA9IFBhdGgoJy9ldGMvb2NzZXJ2L29jc2Vydi5jb25mJykKWk9ORSA9IFBhdGgoJy9ldGMvdG9sZi9vcGVuY29ubmVjdC9ydS56b25lJykKU09DS0VUID0gJy9ydW4vb2NjdGwuc29ja2V0JwpUQUJMRSA9ICd0b2xmX29jX3JpZ2FfZGV2aWNlcycKTU9ERVMgPSB7J2F1dG8nLCAncnUnLCAnbHYnLCAneXQnfQpQT09MID0gaXBhZGRyZXNzLmlwX25ldHdvcmsoJzEwLjE5LjAuMC8yNCcpCllUX1NVRkZJWEVTID0gKCd5b3V0dWJlLmNvbScsICdnb29nbGV2aWRlby5jb20nLCAneXRpbWcuY29tJywgJ3lvdXR1LmJlJywKICAgICAgICAgICAgICAgJ3lvdXR1YmUtbm9jb29raWUuY29tJywgJ3lvdXR1YmVpLmdvb2dsZWFwaXMuY29tJywKICAgICAgICAgICAgICAgJ3lvdXR1YmUuZ29vZ2xlYXBpcy5jb20nLCAneXQzLmdncGh0LmNvbScpCgoKZGVmIHJ1bihhcmdzLCBzb3VyY2U9Tm9uZSwgY2hlY2s9VHJ1ZSwgdGltZW91dD0zMCk6CiAgICByZXR1cm4gc3VicHJvY2Vzcy5ydW4oYXJncywgaW5wdXQ9c291cmNlLCBjYXB0dXJlX291dHB1dD1UcnVlLCB0ZXh0PVRydWUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgY2hlY2s9Y2hlY2ssIHRpbWVvdXQ9dGltZW91dCkKCgpkZWYgdmFsaWRfY24odmFsdWUpOgogICAgcmV0dXJuIGJvb2wocmUuZnVsbG1hdGNoKHIndG9sZi1vYy1bMC05YS1mXXszMn0nLCB2YWx1ZSkpCgoKZGVmIHZhbGlkX2lwKHZhbHVlKToKICAgIHRyeToKICAgICAgICBhZGRyZXNzID0gaXBhZGRyZXNzLmlwX2FkZHJlc3ModmFsdWUpCiAgICAgICAgcmV0dXJuIGFkZHJlc3MgaW4gUE9PTCBhbmQgMiA8PSBpbnQoc3RyKGFkZHJlc3MpLnNwbGl0KCcuJylbLTFdKSA8PSAyNTQKICAgIGV4Y2VwdCBWYWx1ZUVycm9yOgogICAgICAgIHJldHVybiBGYWxzZQoKCmRlZiB3cml0ZShwYXRoLCB0ZXh0LCBtb2RlPTBvNjAwKToKICAgIGRlc2NyaXB0b3IsIG5hbWUgPSB0ZW1wZmlsZS5ta3N0ZW1wKHByZWZpeD0nLicgKyBwYXRoLm5hbWUsIGRpcj1wYXRoLnBhcmVudCkKICAgIHRyeToKICAgICAgICB3aXRoIG9zLmZkb3BlbihkZXNjcmlwdG9yLCAndycpIGFzIHN0cmVhbToKICAgICAgICAgICAgb3MuZmNobW9kKHN0cmVhbS5maWxlbm8oKSwgbW9kZSkKICAgICAgICAgICAgc3RyZWFtLndyaXRlKHRleHQpCiAgICAgICAgb3MucmVwbGFjZShuYW1lLCBwYXRoKQogICAgZmluYWxseToKICAgICAgICBQYXRoKG5hbWUpLnVubGluayhtaXNzaW5nX29rPVRydWUpCgoKQGNvbnRleHRtYW5hZ2VyCmRlZiBsb2NrZWQoKToKICAgIFJVTlRJTUUubWtkaXIobW9kZT0wbzcwMCwgZXhpc3Rfb2s9VHJ1ZSkKICAgIGRlc2NyaXB0b3IgPSBvcy5vcGVuKFJVTlRJTUUgLyAnbG9jaycsIG9zLk9fQ1JFQVQgfCBvcy5PX1JEV1IgfCBvcy5PX05PRk9MTE9XLCAwbzYwMCkKICAgIHRyeToKICAgICAgICBmY250bC5mbG9jayhkZXNjcmlwdG9yLCBmY250bC5MT0NLX0VYKQogICAgICAgIHlpZWxkCiAgICBmaW5hbGx5OgogICAgICAgIG9zLmNsb3NlKGRlc2NyaXB0b3IpCgoKZGVmIG1vZGVfZm9yKHVzZXJuYW1lKToKICAgIHBhdGggPSBESVJFQ1RPUlkgLyAnZGV2aWNlLW1vZGVzJyAvIHVzZXJuYW1lCiAgICBpZiBub3QgcGF0aC5leGlzdHMoKToKICAgICAgICByZXR1cm4gJ2RlbnknCiAgICBtb2RlID0gcGF0aC5yZWFkX3RleHQoKS5zdHJpcCgpCiAgICBpZiBtb2RlIG5vdCBpbiBNT0RFUzoKICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoJ0ludmFsaWQgc3RvcmVkIGRldmljZSBtb2RlJykKICAgIHJldHVybiBtb2RlCgoKZGVmIGJpbmRpbmdzKCk6CiAgICByZXN1bHQgPSBbXQogICAgZm9yIHBhdGggaW4gc29ydGVkKFJVTlRJTUUuZ2xvYigndG9sZi1vYy0qJykpOgogICAgICAgIHVzZXJuYW1lLCBzZXBhcmF0b3IsIGlkZW50aWZpZXIgPSBwYXRoLm5hbWUucGFydGl0aW9uKCcuJykKICAgICAgICBpZiBub3QgdmFsaWRfY24odXNlcm5hbWUpIG9yIG5vdCBzZXBhcmF0b3Igb3Igbm90IHJlLmZ1bGxtYXRjaChyJ1swLTldezEsMjB9JywgaWRlbnRpZmllcik6CiAgICAgICAgICAgIHJhaXNlIFJ1bnRpbWVFcnJvcignSW52YWxpZCBydW50aW1lIGlkZW50aXR5JykKICAgICAgICBhZGRyZXNzID0gcGF0aC5yZWFkX3RleHQoKS5zdHJpcCgpCiAgICAgICAgaWYgbm90IHZhbGlkX2lwKGFkZHJlc3MpOgogICAgICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoJ0ludmFsaWQgcnVudGltZSBsZWFzZScpCiAgICAgICAgcmVzdWx0LmFwcGVuZCgodXNlcm5hbWUsIGlkZW50aWZpZXIsIGFkZHJlc3MpKQogICAgcmV0dXJuIHJlc3VsdAoKCmRlZiBydWxlcyh6b25lLCBsZWFzZXMsIGRucywgbm93KToKICAgICIiIkJ1aWxkIG9uZSBhdG9taWMgcmVwbGFjZW1lbnQsIHVzaW5nIG93biBSVS9ZVCBzZXRzIGFuZCBvd24gbWFya3MuIiIiCiAgICBuZXR3b3JrcyA9IFtdCiAgICBmb3IgbGluZSBpbiB6b25lLnNwbGl0bGluZXMoKToKICAgICAgICBsaW5lID0gbGluZS5zcGxpdCgnIycsIDEpWzBdLnN0cmlwKCkKICAgICAgICBpZiBsaW5lOgogICAgICAgICAgICBuZXR3b3JrID0gaXBhZGRyZXNzLmlwX25ldHdvcmsobGluZSwgc3RyaWN0PUZhbHNlKQogICAgICAgICAgICBpZiBuZXR3b3JrLnZlcnNpb24gIT0gNDoKICAgICAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1JVIHpvbmUgbXVzdCBjb250YWluIElQdjQgbmV0d29ya3MnKQogICAgICAgICAgICBuZXR3b3Jrcy5hcHBlbmQoc3RyKG5ldHdvcmspKQogICAgaWYgbm90IG5ldHdvcmtzOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1JVIHpvbmUgaXMgZW1wdHknKQogICAgbGluZXMgPSBbJ3RhYmxlIGluZXQgJyArIFRBQkxFICsgJyB7JywKICAgICAgICAgICAgICdzZXQgcnU0IHsgdHlwZSBpcHY0X2FkZHI7IGZsYWdzIGludGVydmFsOyBhdXRvLW1lcmdlOyBlbGVtZW50cyA9IHsgJwogICAgICAgICAgICAgKyAnLCAnLmpvaW4obmV0d29ya3MpICsgJyB9OyB9J10KICAgIGZvciBraW5kIGluICgncnVfZG9tYWluczQnLCAneXRfZG9tYWluczQnKToKICAgICAgICBhZGRyZXNzZXMgPSBzb3J0ZWQoc3RyKGlwYWRkcmVzcy5JUHY0QWRkcmVzcyhhZGRyZXNzKSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgZm9yIGFkZHJlc3MsIGV4cGlyeSBpbiBkbnMuZ2V0KGtpbmQsIHt9KS5pdGVtcygpCiAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIGZsb2F0KGV4cGlyeSkgPiBub3cpCiAgICAgICAgbGluZXMuYXBwZW5kKCdzZXQgJyArIGtpbmQgKyAnIHsgdHlwZSBpcHY0X2FkZHI7JwogICAgICAgICAgICAgICAgICAgICArICgnIGVsZW1lbnRzID0geyAnICsgJywgJy5qb2luKGFkZHJlc3NlcykgKyAnIH07JyBpZiBhZGRyZXNzZXMgZWxzZSAnJykgKyAnIH0nKQogICAgZm9yIG1vZGUgaW4gKCdydScsICdsdicsICdhdXRvJywgJ3l0JywgJ2RlbnknKToKICAgICAgICBhZGRyZXNzZXMgPSBzb3J0ZWQoe2FkZHJlc3MgZm9yIF8sIF8sIGFkZHJlc3MsIHZhbHVlIGluIGxlYXNlcyBpZiB2YWx1ZSA9PSBtb2RlfSkKICAgICAgICBpZiBhbnkobm90IHZhbGlkX2lwKGFkZHJlc3MpIGZvciBhZGRyZXNzIGluIGFkZHJlc3Nlcyk6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ0xlYXNlIG91dHNpZGUgUmlnYSBwb29sJykKICAgICAgICBsaW5lcy5hcHBlbmQoJ3NldCBkZXZpY2VfJyArIG1vZGUgKyAnIHsgdHlwZSBpcHY0X2FkZHI7JwogICAgICAgICAgICAgICAgICAgICArICgnIGVsZW1lbnRzID0geyAnICsgJywgJy5qb2luKGFkZHJlc3NlcykgKyAnIH07JyBpZiBhZGRyZXNzZXMgZWxzZSAnJykgKyAnIH0nKQogICAgbGluZXMuZXh0ZW5kKFsnY2hhaW4gcm91dGVfZGV2aWNlcyB7IHR5cGUgZmlsdGVyIGhvb2sgcHJlcm91dGluZyBwcmlvcml0eSAtMTQ1OyBwb2xpY3kgYWNjZXB0OycsCiAgICAgICAgICAgICAgICAgICdpcCBzYWRkciBAZGV2aWNlX2RlbnkgY291bnRlciBkcm9wJywKICAgICAgICAgICAgICAgICAgJ2lwIHNhZGRyIEBkZXZpY2VfcnUgbWV0YSBtYXJrIHNldCAweDE5MiBjb3VudGVyJ10pCiAgICBmb3IgbW9kZSBpbiAoJ2x2JywgJ2F1dG8nLCAneXQnKToKICAgICAgICBsaW5lcy5hcHBlbmQoJ2lwIHNhZGRyIEBkZXZpY2VfJyArIG1vZGUgKyAnIG1ldGEgbWFyayBzZXQgMHgxOTEgY291bnRlcicpCiAgICBmb3IgbW9kZSBpbiAoJ2F1dG8nLCAneXQnKToKICAgICAgICBmb3IgbmFtZSBpbiAoJ3J1NCcsICdydV9kb21haW5zNCcpOgogICAgICAgICAgICBsaW5lcy5hcHBlbmQoJ2lwIHNhZGRyIEBkZXZpY2VfJyArIG1vZGUgKyAnIGlwIGRhZGRyIEAnICsgbmFtZQogICAgICAgICAgICAgICAgICAgICAgICAgKyAnIG1ldGEgbWFyayBzZXQgMHgxOTIgY291bnRlcicpCiAgICBsaW5lcy5hcHBlbmQoJ2lwIHNhZGRyIEBkZXZpY2VfeXQgaXAgZGFkZHIgQHl0X2RvbWFpbnM0IG1ldGEgbWFyayBzZXQgMHgxOTIgY291bnRlcicpCiAgICBsaW5lcy5leHRlbmQoWyd9JywgJ30nXSkKICAgIHJldHVybiAnXG4nLmpvaW4obGluZXMpICsgJ1xuJwoKCmRlZiBwb2xpY3lfcnVsZXMoY3JlYXRlPUZhbHNlKToKICAgIHJvd3MgPSBqc29uLmxvYWRzKHJ1bihbJ2lwJywgJy1qJywgJy00JywgJ3J1bGUnLCAnc2hvdyddKS5zdGRvdXQpCiAgICBmb3IgcHJpb3JpdHksIG1hcmssIHRhYmxlIGluICgoMTAxNywgJzB4MTkyJywgJzExOCcpLCAoMTAxOCwgJzB4MTkxJywgJ21haW4nKSk6CiAgICAgICAgbWF0Y2hlcyA9IFtyb3cgZm9yIHJvdyBpbiByb3dzIGlmIHJvdy5nZXQoJ3ByaW9yaXR5JykgPT0gcHJpb3JpdHldCiAgICAgICAgaWYgbWF0Y2hlczoKICAgICAgICAgICAgaWYgbGVuKG1hdGNoZXMpICE9IDEgb3Igc3RyKG1hdGNoZXNbMF0uZ2V0KCdmd21hcmsnKSkgIT0gbWFyayBvciBzdHIobWF0Y2hlc1swXS5nZXQoJ3RhYmxlJykpICE9IHRhYmxlOgogICAgICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCdQb2xpY3kgcHJpb3JpdHkgY29uZmxpY3Q6ICcgKyBzdHIocHJpb3JpdHkpKQogICAgICAgIGVsaWYgY3JlYXRlOgogICAgICAgICAgICBydW4oWydpcCcsICctNCcsICdydWxlJywgJ2FkZCcsICdwcmlvcml0eScsIHN0cihwcmlvcml0eSksICdmd21hcmsnLCBtYXJrLCAnbG9va3VwJywgdGFibGVdKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIHJhaXNlIFJ1bnRpbWVFcnJvcignUGVyc29uYWwgcG9saWN5IHJ1bGUgbWlzc2luZzogJyArIHN0cihwcmlvcml0eSkpCgoKZGVmIGVuc3VyZV9yb3V0ZXMoKToKICAgIHBvbGljeV9ydWxlcyhjcmVhdGU9VHJ1ZSkKICAgIHJ1bihbJ2lwJywgJy00JywgJ3JvdXRlJywgJ3JlcGxhY2UnLCAnZGVmYXVsdCcsICdkZXYnLCAnZ3JlbW9zY293JywgJ3RhYmxlJywgJzExOCddKQoKCmRlZiBhcHBseSgpOgogICAgZW5zdXJlX3JvdXRlcygpCiAgICBjYWNoZSA9IFJVTlRJTUUgLyAnZG5zLmpzb24nCiAgICBkbnMgPSBqc29uLmxvYWRzKGNhY2hlLnJlYWRfdGV4dCgpKSBpZiBjYWNoZS5leGlzdHMoKSBlbHNlIHt9CiAgICBsZWFzZXMgPSBbKHVzZXIsIGlkZW50aWZpZXIsIGFkZHJlc3MsIG1vZGVfZm9yKHVzZXIpKSBmb3IgdXNlciwgaWRlbnRpZmllciwgYWRkcmVzcyBpbiBiaW5kaW5ncygpXQogICAgc291cmNlID0gcnVsZXMoWk9ORS5yZWFkX3RleHQoKSwgbGVhc2VzLCBkbnMsIHRpbWUudGltZSgpKQogICAgaWYgcnVuKFsnbmZ0JywgJ2xpc3QnLCAndGFibGUnLCAnaW5ldCcsIFRBQkxFXSwgY2hlY2s9RmFsc2UpLnJldHVybmNvZGUgPT0gMDoKICAgICAgICBzb3VyY2UgPSAnZGVsZXRlIHRhYmxlIGluZXQgJyArIFRBQkxFICsgJ1xuJyArIHNvdXJjZQogICAgcnVuKFsnbmZ0JywgJy1mJywgJy0nXSwgc291cmNlKQoKCmRlZiBkaXNjb25uZWN0KHVzZXJuYW1lKToKICAgIHJ1bihbJ29jY3RsJywgJy1zJywgU09DS0VULCAnZGlzY29ubmVjdCcsICd1c2VyJywgdXNlcm5hbWVdLCBjaGVjaz1GYWxzZSkKICAgIHJ1bihbJ29jY3RsJywgJy1zJywgU09DS0VULCAnLS1qc29uJywgJ3Nob3cnLCAndXNlcnMnXSkKICAgIHJlc3VsdCA9IHJ1bihbJ29jY3RsJywgJy1zJywgU09DS0VULCAnLS1qc29uJywgJ3Nob3cnLCAndXNlcicsIHVzZXJuYW1lXSwgY2hlY2s9RmFsc2UpCiAgICBpZiByZXN1bHQucmV0dXJuY29kZSAhPSAyOgogICAgICAgIHJhaXNlIFJ1bnRpbWVFcnJvcignRGV2aWNlIGRpc2Nvbm5lY3Qgbm90IGFja25vd2xlZGdlZCcpCgoKZGVmIGNsZWFyX2Nvbm5lY3Rpb25zKHVzZXJuYW1lKToKICAgIGlmIHNodXRpbC53aGljaCgnY29ubnRyYWNrJyk6CiAgICAgICAgZm9yIHVzZXIsIF8sIGFkZHJlc3MgaW4gYmluZGluZ3MoKToKICAgICAgICAgICAgaWYgdXNlciA9PSB1c2VybmFtZToKICAgICAgICAgICAgICAgIHJ1bihbJ2Nvbm50cmFjaycsICctRCcsICctZicsICdpcHY0JywgJy1zJywgYWRkcmVzc10sIGNoZWNrPUZhbHNlKQogICAgICAgIHJldHVybiBGYWxzZQogICAgcmV0dXJuIGFueSh1c2VyID09IHVzZXJuYW1lIGZvciB1c2VyLCBfLCBfIGluIGJpbmRpbmdzKCkpCgoKZGVmIGRuc19raW5kKG5hbWUpOgogICAgbmFtZSA9IG5hbWUucnN0cmlwKCcuJykubG93ZXIoKQogICAgaWYgbmFtZS5lbmRzd2l0aCgoJy5ydScsICcuc3UnLCAnLnhuLS1wMWFpJykpOgogICAgICAgIHJldHVybiAncnVfZG9tYWluczQnCiAgICBpZiBhbnkobmFtZSA9PSBzdWZmaXggb3IgbmFtZS5lbmRzd2l0aCgnLicgKyBzdWZmaXgpIGZvciBzdWZmaXggaW4gWVRfU1VGRklYRVMpOgogICAgICAgIHJldHVybiAneXRfZG9tYWluczQnCiAgICByZXR1cm4gTm9uZQoKCmRlZiBwYXJzZV9kbnMoc291cmNlLCBub3csIHNlZW49Tm9uZSwgb2JzZXJ2ZWQ9Tm9uZSk6CiAgICByZXN1bHQgPSB7J3J1X2RvbWFpbnM0Jzoge30sICd5dF9kb21haW5zNCc6IHt9fQogICAga2luZCwgYW5zd2VyLCBoZWFkZXIgPSBOb25lLCBGYWxzZSwgJycKICAgIGZvciBsaW5lIGluIHNvdXJjZS5zcGxpdGxpbmVzKCk6CiAgICAgICAgaWYgJyBDUiAnIGluIGxpbmU6CiAgICAgICAgICAgIGtpbmQsIGFuc3dlciA9IE5vbmUsIEZhbHNlCiAgICAgICAgICAgIGhlYWRlciA9IGxpbmUKICAgICAgICAgICAgbWF0Y2ggPSByZS5zZWFyY2gocicgKFteIF0rKS9JTi8oPzpBfEhUVFBTKSQnLCBsaW5lKQogICAgICAgICAgICBpZiBtYXRjaCBhbmQgcmUuc2VhcmNoKHInXGIxMFwuMTlcLjBcLig/OlswLTldezEsM30pKD89WzojL1xzXSknLCBsaW5lKToKICAgICAgICAgICAgICAgIGtpbmQgPSBkbnNfa2luZChtYXRjaC5ncm91cCgxKSkKICAgICAgICAgICAgY29udGludWUKICAgICAgICBpZiBsaW5lLnN0YXJ0c3dpdGgoJzs7IEFOU1dFUiBTRUNUSU9OOicpOgogICAgICAgICAgICBhbnN3ZXIgPSBUcnVlCiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgaWYgbGluZS5zdGFydHN3aXRoKCc7OyAnKToKICAgICAgICAgICAgYW5zd2VyID0gRmFsc2UKICAgICAgICBpZiBraW5kIGFuZCBhbnN3ZXI6CiAgICAgICAgICAgIG1hdGNoID0gcmUubWF0Y2gocideXFMrXHMrKFxkKylccytJTlxzK0FccysoXFMrKVxzKiQnLCBsaW5lKQogICAgICAgICAgICBpZiBtYXRjaDoKICAgICAgICAgICAgICAgIGFkZHJlc3MgPSBpcGFkZHJlc3MuSVB2NEFkZHJlc3MobWF0Y2guZ3JvdXAoMikpCiAgICAgICAgICAgICAgICBpZiBhZGRyZXNzLmlzX2dsb2JhbDoKICAgICAgICAgICAgICAgICAgICAjIElkZW50aWNhbCBoaXN0b3JpY2FsIHJlY29yZHMgbXVzdCBub3QgZ2FpbiBhIGZyZXNoIFRUTAogICAgICAgICAgICAgICAgICAgICMgd2hlbmV2ZXIgYW4gYWN0aXZlIGNhcHR1cmUgZmlsZSByZWNlaXZlcyB1bnJlbGF0ZWQgZGF0YS4KICAgICAgICAgICAgICAgICAgICBrZXkgPSBoYXNobGliLnNoYTI1NigoaGVhZGVyICsgJ1xuJyArIGxpbmUpLmVuY29kZSgpKS5oZXhkaWdlc3QoKQogICAgICAgICAgICAgICAgICAgIGV4cGlyeSA9IChzZWVuIG9yIHt9KS5nZXQoa2V5LCBub3cgKyBtaW4oaW50KG1hdGNoLmdyb3VwKDEpKSwgMjE2MDApKQogICAgICAgICAgICAgICAgICAgIGlmIG9ic2VydmVkIGlzIG5vdCBOb25lOgogICAgICAgICAgICAgICAgICAgICAgICBvYnNlcnZlZFtrZXldID0gZXhwaXJ5CiAgICAgICAgICAgICAgICAgICAgcmVzdWx0W2tpbmRdW3N0cihhZGRyZXNzKV0gPSBtYXgoZXhwaXJ5LCByZXN1bHRba2luZF0uZ2V0KHN0cihhZGRyZXNzKSwgMCkpCiAgICByZXR1cm4gcmVzdWx0CgoKZGVmIHJlZnJlc2hfZG5zKCk6CiAgICBiYXNlID0gUGF0aCgnL3Zhci9saWIvdG9sZi1vcGVuY29ubmVjdCcpCiAgICBmaWxlcyA9IHNvcnRlZChiYXNlLmdsb2IoJ2Ruc3RhcC0qLmZzdHJtJyksIGtleT1sYW1iZGEgcDogcC5zdGF0KCkuc3RfbXRpbWUsIHJldmVyc2U9VHJ1ZSlbOjJdCiAgICBpZiBub3QgZmlsZXMgYW5kIChiYXNlIC8gJ2Ruc3RhcC5mc3RybScpLmV4aXN0cygpOgogICAgICAgIGZpbGVzID0gW2Jhc2UgLyAnZG5zdGFwLmZzdHJtJ10KICAgIGNvbGxlY3RlZCA9IHsncnVfZG9tYWluczQnOiB7fSwgJ3l0X2RvbWFpbnM0Jzoge319CiAgICBzZWVuX3BhdGggPSBSVU5USU1FIC8gJ2Rucy1zZWVuLmpzb24nCiAgICBzZWVuID0ganNvbi5sb2FkcyhzZWVuX3BhdGgucmVhZF90ZXh0KCkpIGlmIHNlZW5fcGF0aC5leGlzdHMoKSBlbHNlIHt9CiAgICBvYnNlcnZlZCA9IHt9CiAgICBmb3IgcGF0aCBpbiByZXZlcnNlZChmaWxlcyk6CiAgICAgICAgcmVzdWx0ID0gcnVuKFsnZG5zdGFwLXJlYWQnLCAnLXAnLCBzdHIocGF0aCldLCB0aW1lb3V0PTQ1KQogICAgICAgIHBhcnNlZCA9IHBhcnNlX2RucyhyZXN1bHQuc3Rkb3V0LCBtaW4odGltZS50aW1lKCksIHBhdGguc3RhdCgpLnN0X210aW1lKSwgc2Vlbiwgb2JzZXJ2ZWQpCiAgICAgICAgZm9yIGtpbmQgaW4gY29sbGVjdGVkOgogICAgICAgICAgICBmb3IgYWRkcmVzcywgZXhwaXJ5IGluIHBhcnNlZFtraW5kXS5pdGVtcygpOgogICAgICAgICAgICAgICAgY29sbGVjdGVkW2tpbmRdW2FkZHJlc3NdID0gbWF4KGV4cGlyeSwgY29sbGVjdGVkW2tpbmRdLmdldChhZGRyZXNzLCAwKSkKICAgIHdpdGggbG9ja2VkKCk6CiAgICAgICAgY2FjaGUgPSBSVU5USU1FIC8gJ2Rucy5qc29uJwogICAgICAgIHByZXZpb3VzID0ganNvbi5sb2FkcyhjYWNoZS5yZWFkX3RleHQoKSkgaWYgY2FjaGUuZXhpc3RzKCkgZWxzZSB7fQogICAgICAgIGZvciBraW5kIGluIGNvbGxlY3RlZDoKICAgICAgICAgICAgZm9yIGFkZHJlc3MsIGV4cGlyeSBpbiBwcmV2aW91cy5nZXQoa2luZCwge30pLml0ZW1zKCk6CiAgICAgICAgICAgICAgICBpZiBleHBpcnkgPiB0aW1lLnRpbWUoKToKICAgICAgICAgICAgICAgICAgICBjb2xsZWN0ZWRba2luZF1bYWRkcmVzc10gPSBtYXgoZXhwaXJ5LCBjb2xsZWN0ZWRba2luZF0uZ2V0KGFkZHJlc3MsIDApKQogICAgICAgICAgICBjb2xsZWN0ZWRba2luZF0gPSB7YWRkcmVzczogZXhwaXJ5IGZvciBhZGRyZXNzLCBleHBpcnkgaW4gY29sbGVjdGVkW2tpbmRdLml0ZW1zKCkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIGV4cGlyeSA+IHRpbWUudGltZSgpfQogICAgICAgIHdyaXRlKGNhY2hlLCBqc29uLmR1bXBzKGNvbGxlY3RlZCkpCiAgICAgICAgd3JpdGUoc2Vlbl9wYXRoLCBqc29uLmR1bXBzKG9ic2VydmVkKSkKICAgICAgICBhcHBseSgpCiAgICAgICAgd3JpdGUoUlVOVElNRSAvICdsYXN0LWRucy1yZWZyZXNoJywgc3RyKHRpbWUudGltZSgpKSkKCgpkZWYgaG9vaygpOgogICAgdXNlcm5hbWUgPSBvcy5lbnZpcm9uLmdldCgnVVNFUk5BTUUnLCAnJykKICAgIGlkZW50aWZpZXIgPSBvcy5lbnZpcm9uLmdldCgnSUQnLCAnJykKICAgIGFkZHJlc3MgPSBvcy5lbnZpcm9uLmdldCgnSVBfUkVNT1RFJywgJycpCiAgICBpZiBub3QgcmUuZnVsbG1hdGNoKHInWzAtOV17MSwyMH0nLCBpZGVudGlmaWVyKSBvciBub3QgdmFsaWRfaXAoYWRkcmVzcyk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignSW52YWxpZCBob29rIGxlYXNlJykKICAgIHBlcnNvbmFsID0gdXNlcm5hbWUuc3RhcnRzd2l0aCgndG9sZi1vYy0nKQogICAgaWYgcGVyc29uYWwgYW5kIG5vdCB2YWxpZF9jbih1c2VybmFtZSk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignSW52YWxpZCBob29rIGlkZW50aXR5JykKICAgIHdpdGggbG9ja2VkKCk6CiAgICAgICAgcmVhc29uID0gb3MuZW52aXJvbi5nZXQoJ1JFQVNPTicpCiAgICAgICAgaWYgcmVhc29uID09ICdjb25uZWN0JzoKICAgICAgICAgICAgIyBJUCByZXVzZSBieSBlaXRoZXIgYSBsZWdhY3kgb3IgcGVyc29uYWwgY2xpZW50IHJlbW92ZXMgc3RhbGUgYmluZGluZ3MuCiAgICAgICAgICAgIGZvciB1c2VyLCBzZXNzaW9uX2lkLCBpcCBpbiBiaW5kaW5ncygpOgogICAgICAgICAgICAgICAgaWYgaXAgPT0gYWRkcmVzczoKICAgICAgICAgICAgICAgICAgICAoUlVOVElNRSAvICh1c2VyICsgJy4nICsgc2Vzc2lvbl9pZCkpLnVubGluaygpCiAgICAgICAgICAgIGlmIHBlcnNvbmFsOgogICAgICAgICAgICAgICAgd3JpdGUoUlVOVElNRSAvICh1c2VybmFtZSArICcuJyArIGlkZW50aWZpZXIpLCBhZGRyZXNzKQogICAgICAgICAgICB0cnk6CiAgICAgICAgICAgICAgICBhcHBseSgpCiAgICAgICAgICAgICAgICBpZiBwZXJzb25hbCBhbmQgbW9kZV9mb3IodXNlcm5hbWUpID09ICdkZW55JzoKICAgICAgICAgICAgICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoJ0RldmljZSBpcyBub3QgcmVnaXN0ZXJlZCcpCiAgICAgICAgICAgIGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgICAgICAgICAjIEEgZGVueSBsZWFzZSBzdGF5cyBpbiBwbGFjZSBmb3IgYW4gdW5yZWdpc3RlcmVkIHBlcnNvbmFsIENOLgogICAgICAgICAgICAgICAgcmFpc2UKICAgICAgICBlbGlmIHJlYXNvbiA9PSAnZGlzY29ubmVjdCc6CiAgICAgICAgICAgIHBhdGggPSBSVU5USU1FIC8gKHVzZXJuYW1lICsgJy4nICsgaWRlbnRpZmllcikKICAgICAgICAgICAgaWYgcGVyc29uYWwgYW5kIHBhdGguZXhpc3RzKCkgYW5kIHBhdGgucmVhZF90ZXh0KCkuc3RyaXAoKSA9PSBhZGRyZXNzOgogICAgICAgICAgICAgICAgcGF0aC51bmxpbmsoKQogICAgICAgICAgICBhcHBseSgpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignVW5zdXBwb3J0ZWQgaG9vayByZWFzb24nKQoKCmRlZiBoZWFsdGgoKToKICAgIGV4cGVjdGVkID0gKERJUkVDVE9SWSAvICd1ay1jbGllbnQtY2Euc2hhMjU2JykucmVhZF90ZXh0KCkuc3RyaXAoKQogICAgY2EgPSBESVJFQ1RPUlkgLyAndWstY2xpZW50LWNhLnBlbScKICAgIGRlciA9IHN1YnByb2Nlc3MucnVuKFsnb3BlbnNzbCcsICd4NTA5JywgJy1pbicsIHN0cihjYSksICctb3V0Zm9ybScsICdERVInXSwKICAgICAgICAgICAgICAgICAgICAgICAgIGNoZWNrPVRydWUsIGNhcHR1cmVfb3V0cHV0PVRydWUsIHRpbWVvdXQ9MTApLnN0ZG91dAogICAgaWYgaGFzaGxpYi5zaGEyNTYoZGVyKS5oZXhkaWdlc3QoKSAhPSBleHBlY3RlZDoKICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoJ0NBIGZpbmdlcnByaW50IG1pc21hdGNoJykKICAgIHJ1bihbJ29wZW5zc2wnLCAndmVyaWZ5JywgJy1DQWZpbGUnLCBzdHIoY2EpLCAnLUNSTGZpbGUnLAogICAgICAgICBzdHIoRElSRUNUT1JZIC8gJ3VrLWNsaWVudC1jYS5jcmwucGVtJyksICctY3JsX2NoZWNrJywgc3RyKGNhKV0pCiAgICBjb25maWcgPSBDT05GLnJlYWRfdGV4dCgpCiAgICBmb3IgbGluZSBpbiAoJ2Nvbm5lY3Qtc2NyaXB0ID0gL3Vzci9sb2NhbC9zYmluL3RvbGYtb2MtcmlnYS1kZXZpY2UtaG9vaycsCiAgICAgICAgICAgICAgICAgJ2Rpc2Nvbm5lY3Qtc2NyaXB0ID0gL3Vzci9sb2NhbC9zYmluL3RvbGYtb2MtcmlnYS1kZXZpY2UtaG9vaycsCiAgICAgICAgICAgICAgICAgJ2NvbmZpZy1wZXItdXNlciA9ICcgKyBzdHIoUFJPRklMRVMpICsgJy8nKToKICAgICAgICBpZiBsaW5lIG5vdCBpbiBjb25maWcuc3BsaXRsaW5lcygpOgogICAgICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoJ0RldmljZSBob29rIGNvbmZpZ3VyYXRpb24gbWlzc2luZycpCiAgICBydW4oWydvY2N0bCcsICctcycsIFNPQ0tFVCwgJy0tanNvbicsICdzaG93JywgJ3VzZXJzJ10pCiAgICBmb3IgbmFtZSBpbiAoJ2RldmljZV9kZW55JywgJ3J1NCcsICdydV9kb21haW5zNCcsICd5dF9kb21haW5zNCcpOgogICAgICAgIHJ1bihbJ25mdCcsICdsaXN0JywgJ3NldCcsICdpbmV0JywgVEFCTEUsIG5hbWVdKQogICAgcmVmcmVzaGVkID0gZmxvYXQoKFJVTlRJTUUgLyAnbGFzdC1kbnMtcmVmcmVzaCcpLnJlYWRfdGV4dCgpKQogICAgaWYgdGltZS50aW1lKCkgLSByZWZyZXNoZWQgPiAxODA6CiAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCdETlMgcmVmcmVzaCBpcyBzdGFsZScpCiAgICByb3V0ZXMgPSBydW4oWydpcCcsICctNCcsICdyb3V0ZScsICdzaG93JywgJ3RhYmxlJywgJzExOCddKS5zdGRvdXQKICAgIGlmICdkZWZhdWx0IGRldiBncmVtb3Njb3cnIG5vdCBpbiByb3V0ZXM6CiAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCdNb3Njb3cgcm91dGUgbWlzc2luZycpCiAgICBwb2xpY3lfcnVsZXMoKQogICAgcmV0dXJuIHsnc3RhdHVzJzogJ29rJywgJ3ZlcnNpb24nOiAxLCAnY2FTaGEyNTYnOiBleHBlY3RlZCwKICAgICAgICAgICAgJ2RldmljZVJvdXRpbmcnOiBUcnVlLCAnaXNzdWFuY2UnOiBGYWxzZX0KCgpkZWYgbWFpbihhcmd2KToKICAgIG9wZXJhdGlvbiA9IGFyZ3ZbMF0gaWYgYXJndiBlbHNlICcnCiAgICBpZiBvcGVyYXRpb24gPT0gJ2hvb2snIGFuZCBsZW4oYXJndikgPT0gMToKICAgICAgICBob29rKCkKICAgICAgICByZXR1cm4gTm9uZQogICAgaWYgb3BlcmF0aW9uID09ICdhcHBseScgYW5kIGxlbihhcmd2KSA9PSAxOgogICAgICAgIHdpdGggbG9ja2VkKCk6CiAgICAgICAgICAgIGFwcGx5KCkKICAgICAgICByZXR1cm4gTm9uZQogICAgaWYgb3BlcmF0aW9uID09ICdkbnMtcmVmcmVzaCcgYW5kIGxlbihhcmd2KSA9PSAxOgogICAgICAgIHJlZnJlc2hfZG5zKCkKICAgICAgICByZXR1cm4gTm9uZQogICAgaWYgb3BlcmF0aW9uID09ICdoZWFsdGgnIGFuZCBsZW4oYXJndikgPT0gMToKICAgICAgICByZXR1cm4gaGVhbHRoKCkKICAgIGlmIGxlbihhcmd2KSA8IDIgb3Igbm90IHZhbGlkX2NuKGFyZ3ZbMV0pOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ0ludmFsaWQgb3BlcmF0aW9uIG9yIGlkZW50aXR5JykKICAgIHVzZXJuYW1lID0gYXJndlsxXQogICAgaWYgb3BlcmF0aW9uID09ICdzZXNzaW9uJyBhbmQgbGVuKGFyZ3YpID09IDI6CiAgICAgICAgcnVuKFsnb2NjdGwnLCAnLXMnLCBTT0NLRVQsICctLWpzb24nLCAnc2hvdycsICd1c2VycyddKQogICAgICAgIHJlc3VsdCA9IHJ1bihbJ29jY3RsJywgJy1zJywgU09DS0VULCAnLS1qc29uJywgJ3Nob3cnLCAndXNlcicsIHVzZXJuYW1lXSwgY2hlY2s9RmFsc2UpCiAgICAgICAgaWYgcmVzdWx0LnJldHVybmNvZGUgbm90IGluICgwLCAyKToKICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCdTZXNzaW9uIHVuYXZhaWxhYmxlJykKICAgICAgICByZXR1cm4geydzdGF0dXMnOiAnb2snLCAndXNlcm5hbWUnOiB1c2VybmFtZSwgJ2Nvbm5lY3RlZCc6IHJlc3VsdC5yZXR1cm5jb2RlID09IDB9CiAgICBpZiBvcGVyYXRpb24gPT0gJ3NldCcgYW5kIGxlbihhcmd2KSA9PSAzIGFuZCBhcmd2WzJdIGluIE1PREVTOgogICAgICAgIG1vZGUgPSBhcmd2WzJdCiAgICAgICAgd2l0aCBsb2NrZWQoKToKICAgICAgICAgICAgcGF0aCA9IERJUkVDVE9SWSAvICdkZXZpY2UtbW9kZXMnIC8gdXNlcm5hbWUKICAgICAgICAgICAgb2xkID0gbW9kZV9mb3IodXNlcm5hbWUpCiAgICAgICAgICAgIHdyaXRlKHBhdGgsIG1vZGUgKyAnXG4nKQogICAgICAgICAgICB0cnk6CiAgICAgICAgICAgICAgICBhcHBseSgpCiAgICAgICAgICAgICAgICB3cml0ZShQUk9GSUxFUyAvIHVzZXJuYW1lLCAnbWF4LXNhbWUtY2xpZW50cyA9IDFcbicsIDBvNjQ0KQogICAgICAgICAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgICAgICAgICAgaWYgb2xkID09ICdkZW55JzoKICAgICAgICAgICAgICAgICAgICBwYXRoLnVubGluayhtaXNzaW5nX29rPVRydWUpCiAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgIHdyaXRlKHBhdGgsIG9sZCArICdcbicpCiAgICAgICAgICAgICAgICBhcHBseSgpCiAgICAgICAgICAgICAgICByYWlzZQogICAgICAgICAgICByZWNvbm5lY3QgPSBjbGVhcl9jb25uZWN0aW9ucyh1c2VybmFtZSkgaWYgb2xkICE9IG1vZGUgZWxzZSBGYWxzZQogICAgICAgIGlmIHJlY29ubmVjdDoKICAgICAgICAgICAgZGlzY29ubmVjdCh1c2VybmFtZSkKICAgICAgICByZXR1cm4geydzdGF0dXMnOiAnb2snLCAndXNlcm5hbWUnOiB1c2VybmFtZSwgJ21vZGUnOiBtb2RlfQogICAgaWYgb3BlcmF0aW9uID09ICdyZW1vdmUnIGFuZCBsZW4oYXJndikgPT0gMjoKICAgICAgICB3aXRoIGxvY2tlZCgpOgogICAgICAgICAgICAoRElSRUNUT1JZIC8gJ2RldmljZS1tb2RlcycgLyB1c2VybmFtZSkudW5saW5rKG1pc3Npbmdfb2s9VHJ1ZSkKICAgICAgICAgICAgKFBST0ZJTEVTIC8gdXNlcm5hbWUpLnVubGluayhtaXNzaW5nX29rPVRydWUpCiAgICAgICAgICAgIGFwcGx5KCkKICAgICAgICAgICAgY2xlYXJfY29ubmVjdGlvbnModXNlcm5hbWUpCiAgICAgICAgZGlzY29ubmVjdCh1c2VybmFtZSkKICAgICAgICByZXR1cm4geydzdGF0dXMnOiAnb2snLCAndXNlcm5hbWUnOiB1c2VybmFtZSwgJ3JlbW92ZWQnOiBUcnVlfQogICAgcmFpc2UgVmFsdWVFcnJvcignVW5zdXBwb3J0ZWQgZGV2aWNlIG9wZXJhdGlvbicpCgoKaWYgX19uYW1lX18gPT0gJ19fbWFpbl9fJzoKICAgIHRyeToKICAgICAgICByZXBseSA9IG1haW4oc3lzLmFyZ3ZbMTpdKQogICAgICAgIGlmIHJlcGx5IGlzIG5vdCBOb25lOgogICAgICAgICAgICBwcmludChqc29uLmR1bXBzKHJlcGx5LCBzZXBhcmF0b3JzPSgnLCcsICc6JykpKQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlcnJvcjoKICAgICAgICBwcmludChqc29uLmR1bXBzKHsnc3RhdHVzJzogJ2Vycm9yJywgJ2Vycm9yJzogc3RyKGVycm9yKX0pKQogICAgICAgIHN5cy5leGl0KDEpCg=='}, 'riga-remote.py': {'sha256': 'f6ef82eebe57e863e70ddaf55b2ed27386cc5756445eb8d54660815d96fe8968', 'data': 'IyEvdXNyL2Jpbi9weXRob24zCiIiIkZvcmNlZCBTU0ggY29tbWFuZCBkaXNwYXRjaGVyOyBubyBzaGVsbCBleHBhbnNpb24gb3IgYWNjb3VudCBkYXRhLiIiIgppbXBvcnQgb3MKaW1wb3J0IHJlCmltcG9ydCBzeXMKCmNvbW1hbmQgPSBvcy5lbnZpcm9uLmdldCgnU1NIX09SSUdJTkFMX0NPTU1BTkQnLCAnJykKY29udHJvbGxlciA9ICcvdXNyL2xvY2FsL3NiaW4vdG9sZi1vYy1yaWdhLWRldmljZXMnCmlmIGNvbW1hbmQgPT0gJ3RvbGYtb2Mtbm9kZS1oZWFsdGgnOgogICAgYXJncyA9IFtjb250cm9sbGVyLCAnaGVhbHRoJ10KZWxpZiBjb21tYW5kID09ICd0b2xmLW9jLWNybC1zeW5jJzoKICAgICMgQ29udHJvbGxlciBoZWFsdGggbXVzdCBydW4gb25seSBhZnRlciBzeW5jaHJvbml6YXRpb24gc3VjY2VlZHMuCiAgICBpbXBvcnQgc3VicHJvY2VzcwogICAgcmVzdWx0ID0gc3VicHJvY2Vzcy5ydW4oWycvdXNyL2xvY2FsL3NiaW4vdG9sZi1vYy1yaWdhLWNybC1zeW5jJ10sCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjYXB0dXJlX291dHB1dD1UcnVlLCB0aW1lb3V0PTYwKQogICAgaWYgcmVzdWx0LnJldHVybmNvZGU6CiAgICAgICAgcHJpbnQoJ3sic3RhdHVzIjoiZXJyb3IiLCJlcnJvciI6ImNybF9zeW5jX2ZhaWxlZCJ9JykKICAgICAgICBzeXMuZXhpdCgxKQogICAgYXJncyA9IFtjb250cm9sbGVyLCAnaGVhbHRoJ10KZWxzZToKICAgIG1hdGNoID0gcmUuZnVsbG1hdGNoKHIndG9sZi1vYy0oZGV2aWNlfGRldmljZS1yZW1vdmV8c2Vzc2lvbikgKHRvbGYtb2MtWzAtOWEtZl17MzJ9KSg/OiAoYXV0b3xydXxsdnx5dCkpPycsIGNvbW1hbmQpCiAgICBpZiBub3QgbWF0Y2ggb3IgKG1hdGNoWzFdID09ICdkZXZpY2UnKSAhPSAobWF0Y2hbM10gaXMgbm90IE5vbmUpOgogICAgICAgIHByaW50KCd7InN0YXR1cyI6ImVycm9yIiwiZXJyb3IiOiJjb21tYW5kX25vdF9hbGxvd2VkIn0nKQogICAgICAgIHN5cy5leGl0KDEpCiAgICBhcmdzID0gW2NvbnRyb2xsZXIsIHsnZGV2aWNlJzogJ3NldCcsICdkZXZpY2UtcmVtb3ZlJzogJ3JlbW92ZScsICdzZXNzaW9uJzogJ3Nlc3Npb24nfVttYXRjaFsxXV0sIG1hdGNoWzJdXQogICAgaWYgbWF0Y2hbM106CiAgICAgICAgYXJncy5hcHBlbmQobWF0Y2hbM10pCm9zLmV4ZWN2KGFyZ3NbMF0sIGFyZ3MpCg=='}}
CONF = Path('/etc/ocserv/ocserv.conf')
DIRECTORY = Path('/etc/ocserv/tolf-uk')
PROFILES = Path('/etc/ocserv/tolf-device-config')
RUNTIME = Path('/run/tolf-oc-riga-devices')
ZONE = Path('/etc/tolf/openconnect/ru.zone')
SOCKET = '/run/occtl.socket'
CONTROLLER = Path('/usr/local/sbin/tolf-oc-riga-devices')
REMOTE = Path('/usr/local/sbin/tolf-oc-riga-remote')
HOOK = Path('/usr/local/sbin/tolf-oc-riga-device-hook')
SERVICE = Path('/etc/systemd/system/tolf-oc-riga-devices.service')
REFRESH = Path('/etc/systemd/system/tolf-oc-riga-devices-refresh.service')
TIMER = Path('/etc/systemd/system/tolf-oc-riga-devices-refresh.timer')


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True,
                          timeout=120).stdout


def options(source, name):
    return [match.group(1).strip('"') for line in source.splitlines()
            if (match := re.match(r'^\s*' + re.escape(name) + r'\s*=\s*(.*?)\s*$', line))]


def updated_config(source):
    expected = {'connect-script': str(HOOK), 'disconnect-script': str(HOOK),
                'config-per-user': str(PROFILES) + '/'}
    for name, value in expected.items():
        if options(source, name) not in ([], [value]):
            raise RuntimeError('Existing ' + name + ' needs integration')
    lines = [line for line in source.splitlines() if not re.match(
        r'^\s*(connect-script|disconnect-script|config-per-user)\s*=', line)]
    return '\n'.join(lines) + '\n' + '\n'.join(
        name + ' = ' + value for name, value in expected.items()) + '\n'


def atomic(path, data, mode=0o644):
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    stat = path.stat() if path.exists() else None
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            os.fchmod(stream.fileno(), stat.st_mode & 0o777 if stat else mode)
            if stat:
                os.fchown(stream.fileno(), stat.st_uid, stat.st_gid)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run as root on EDISLV')
    for tool in ('occtl', 'ocserv', 'openssl', 'nft', 'ip', 'dnstap-read', 'systemctl'):
        if not shutil.which(tool):
            raise RuntimeError('Missing tool: ' + tool)
    source = CONF.read_text()
    if options(source, 'ipv4-network') != ['10.19.0.0']:
        raise RuntimeError('Unexpected Riga VPN pool')
    if options(source, 'crl') != [str(DIRECTORY / 'uk-client-ca.crl.pem')]:
        raise RuntimeError('Install Riga UK CA/CRL foundation first')
    config = updated_config(source)
    connected = json.loads(run('occtl', '-s', SOCKET, '--json', 'show', 'users'))
    run('openssl', 'verify', '-CAfile', str(DIRECTORY / 'uk-client-ca.pem'),
        '-CRLfile', str(DIRECTORY / 'uk-client-ca.crl.pem'), '-crl_check',
        str(DIRECTORY / 'uk-client-ca.pem'))
    if not ZONE.is_file():
        raise RuntimeError('Riga RU zone not found')
    routes = [row for row in json.loads(run('ip', '-j', '-4', 'route', 'show', 'table', 'all'))
              if str(row.get('table')) == '118']
    if any(row.get('dst') != 'default' or row.get('dev') != 'gremoscow' for row in routes):
        raise RuntimeError('Route table 118 is already used')
    previous_rules = json.loads(run('ip', '-j', '-4', 'rule', 'show'))
    for row in previous_rules:
        if row.get('priority') in (1017, 1018):
            wanted = ('0x192', '118') if row['priority'] == 1017 else ('0x191', 'main')
            if (str(row.get('fwmark')), str(row.get('table'))) != wanted:
                raise RuntimeError('Riga personal rule priority conflict')
    backup = Path(tempfile.mkdtemp(prefix='devices-backup.', dir=CONF.parent))
    os.chmod(backup, 0o700)
    targets = [CONF, CONTROLLER, REMOTE, HOOK, SERVICE, REFRESH, TIMER]
    previous = {}
    for index, path in enumerate(targets):
        if path.is_symlink():
            raise RuntimeError('Unexpected symlink: ' + str(path))
        saved = backup / ('file-' + str(index))
        previous[path] = saved if path.exists() else None
        if path.exists():
            shutil.copy2(path, saved)
    nft = subprocess.run(['nft', 'list', 'table', 'inet', 'tolf_oc_riga_devices'],
                         capture_output=True, text=True)
    (backup / 'personal-table.nft').write_text(nft.stdout)
    states = {unit.name: {action: subprocess.run(
        ['systemctl', 'is-' + action, unit.name], capture_output=True).returncode == 0
        for action in ('enabled', 'active')} for unit in (SERVICE, TIMER)}
    DIRECTORY.joinpath('device-modes').mkdir(mode=0o700, exist_ok=True)
    PROFILES.mkdir(mode=0o755, exist_ok=True)
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    try:
        # Stop refresh jobs before replacing their executable or rule table.
        for unit in (TIMER, REFRESH, SERVICE):
            subprocess.run(['systemctl', 'stop', unit.name], capture_output=True)
        for name, path in (('riga-devices.py', CONTROLLER), ('riga-remote.py', REMOTE)):
            data = base64.b64decode(PAYLOAD[name]['data'])
            if hashlib.sha256(data).hexdigest() != PAYLOAD[name]['sha256']:
                raise RuntimeError('Embedded script hash mismatch')
            compile(data, name, 'exec')
            atomic(path, data, 0o755)
        atomic(HOOK, b'#!/bin/sh\nexec /usr/local/sbin/tolf-oc-riga-devices hook\n', 0o755)
        candidate = backup / 'config.new'
        candidate.write_text(config)
        run('ocserv', '-t', '-c', str(candidate))
        run(str(CONTROLLER), 'dns-refresh')
        atomic(CONF, config.encode())
        run('occtl', '-s', SOCKET, 'reload')
        # Sessions established before the hook was installed have no lease
        # binding. Reconnect only personal identities, preserving pilot users.
        def identities(value):
            if isinstance(value, str) and re.fullmatch(r'tolf-oc-[0-9a-f]{32}', value):
                yield value
            elif isinstance(value, dict):
                for item in value.values():
                    yield from identities(item)
            elif isinstance(value, list):
                for item in value:
                    yield from identities(item)
        for username in sorted(set(identities(connected))):
            run('occtl', '-s', SOCKET, 'disconnect', 'user', username)
        atomic(SERVICE, (
            '[Unit]\nDescription=TOLF Riga personal device enforcement\n'
            'After=network-online.target\nWants=network-online.target\nBefore=ocserv.service\n'
            '[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=' + str(CONTROLLER) + ' apply\n'
            '[Install]\nWantedBy=multi-user.target\n').encode())
        atomic(REFRESH, (
            '[Unit]\nDescription=Refresh TOLF Riga device DNS routes\n'
            'After=tolf-oc-riga-devices.service\nRequires=tolf-oc-riga-devices.service\n'
            '[Service]\nType=oneshot\nExecStart=' + str(CONTROLLER) + ' dns-refresh\n').encode())
        atomic(TIMER, (
            '[Unit]\nDescription=Refresh TOLF Riga personal rules every minute\n'
            '[Timer]\nOnBootSec=30s\nOnUnitActiveSec=60s\n'
            '[Install]\nWantedBy=timers.target\n').encode())
        run('systemctl', 'daemon-reload')
        run('systemctl', 'enable', '--now', SERVICE.name, TIMER.name)
        run('systemctl', 'start', REFRESH.name)
        print(run(str(CONTROLLER), 'health').strip())
    except Exception:
        for unit in (TIMER, REFRESH, SERVICE):
            subprocess.run(['systemctl', 'stop', unit.name], capture_output=True)
            if unit.name in states and not states[unit.name]['enabled']:
                subprocess.run(['systemctl', 'disable', unit.name], capture_output=True)
        for path, saved in previous.items():
            if saved:
                shutil.copy2(saved, path)
            else:
                path.unlink(missing_ok=True)
        subprocess.run(['nft', 'delete', 'table', 'inet', 'tolf_oc_riga_devices'], capture_output=True)
        if nft.returncode == 0:
            subprocess.run(['nft', '-f', str(backup / 'personal-table.nft')], capture_output=True)
        for priority in (1017, 1018):
            if not any(row.get('priority') == priority for row in previous_rules):
                subprocess.run(['ip', '-4', 'rule', 'del', 'priority', str(priority)], capture_output=True)
        if not routes:
            subprocess.run(['ip', '-4', 'route', 'flush', 'table', '118'], capture_output=True)
        subprocess.run(['systemctl', 'daemon-reload'], capture_output=True)
        for unit in (SERVICE, TIMER):
            if states[unit.name]['active']:
                subprocess.run(['systemctl', 'start', unit.name], capture_output=True)
        subprocess.run(['occtl', '-s', SOCKET, 'reload'], capture_output=True)
        print('ERROR: previous configuration restored. Backup:', backup)
        raise
    print('OK: Riga personal device enforcement installed. Backup:', backup)
    print('UK registration/activation and the Riga website connection are next stages.')
    if not shutil.which('conntrack'):
        print('Mode changes will reconnect active devices until conntrack is installed.')


if __name__ == '__main__':
    main()
