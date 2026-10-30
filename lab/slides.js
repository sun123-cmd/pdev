// The QR always follows the actual site address, including temporary demo URLs.
(() => {
  const section = document.querySelector('.lab-join');
  if (!section || typeof qrcode !== 'function') return;
  const url = new URL('lab/', location.href);
  url.search = ''; url.hash = '';
  const qr = qrcode(0, 'M');
  qr.addData(url.href); qr.make();
  section.querySelector('img').src = qr.createDataURL(5, 4);
  section.querySelector('a').href = url.href;
  section.querySelector('.lab-url').textContent = url.host + url.pathname;
})();
