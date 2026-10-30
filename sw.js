/* MatrixDesk alerts. Upload this file next to index.html (same folder, site root). */
self.addEventListener('install', function(){ self.skipWaiting(); });
self.addEventListener('activate', function(e){ e.waitUntil(self.clients.claim()); });

self.addEventListener('push', function(event){
  var d = {};
  try { d = event.data ? event.data.json() : {}; } catch(e){ d = {body: event.data ? event.data.text() : ''}; }
  var title = d.title || 'MatrixDesk';
  event.waitUntil(self.registration.showNotification(title, {
    body: d.body || '',
    tag: d.tag || 'matrixdesk',
    renotify: true,
    data: {url: d.url || '/dashboard'}
  }));
});

self.addEventListener('notificationclick', function(event){
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || '/dashboard';
  event.waitUntil(self.clients.matchAll({type: 'window', includeUncontrolled: true}).then(function(list){
    for(var i = 0; i < list.length; i++){
      var c = list[i];
      if(c.url.indexOf(self.location.origin) === 0 && 'focus' in c){
        return c.focus().then(function(w){ return (w && 'navigate' in w) ? w.navigate(url) : w; });
      }
    }
    return self.clients.openWindow(url);
  }));
});
