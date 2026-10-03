// Get your Perplexity session cookie value.
//
// Paste this into the browser console (F12 -> Console) while on https://www.perplexity.ai,
// or save it as a bookmarklet. It prints the session cookie and copies its value to the
// clipboard so you can paste it into PERPLEXITY_SESSION_TOKEN.
//
// NOTE: Perplexity's session cookie is HttpOnly, so document.cookie often cannot read it.
// If this prints "not readable", use the manual steps it prints instead.
(function () {
  var jar = {};
  var parts = document.cookie.split(';');
  for (var i = 0; i < parts.length; i++) {
    var c = parts[i];
    var idx = c.indexOf('=');
    if (idx <= 0) continue;
    var key = c.slice(0, idx).trim();
    var val = c.slice(idx + 1).trim();
    try { jar[key] = decodeURIComponent(val); } catch (e) { jar[key] = val; }
  }

  var found = [];
  for (var name in jar) {
    if (name.indexOf('__Secure-pplx.session.') === 0 || name === '__Secure-next-auth.session-token') {
      found.push([name, jar[name]]);
    }
  }

  if (found.length === 0) {
    var msg = [
      'No Perplexity session cookie was readable from JavaScript.',
      '',
      'This is expected: the session cookie is HttpOnly, so document.cookie cannot read it.',
      'Copy it manually instead:',
      '  1. F12 -> Application -> Cookies -> https://www.perplexity.ai',
      '  2. Find "__Secure-pplx.session.<id>" (Google sign-in) or',
      '     "__Secure-next-auth.session-token" (email sign-in).',
      '  3. Double-click the Value and copy the long "eyJ..." string.'
    ].join('\n');
    console.log(msg);
    alert(msg);
    return;
  }

  var value = found[0][1];
  console.log('Perplexity session cookie:\n\n' + found[0][0] + '=' + value + '\n');

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok ? Promise.resolve() : Promise.reject(new Error('copy failed'));
  }

  copyText(value).then(
    function () { console.log('Copied session cookie value to clipboard.'); },
    function () { console.log('Copy failed - copy the value printed above manually.'); }
  );
  alert('Copied your Perplexity session cookie value to the clipboard.\nSee the console for the full value.');
})();
