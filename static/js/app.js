(function () {
    var socket = io('/');
    var MAX_LOG_ENTRIES = 100;
    var currentState = null;
    var currentGestures = {};
    var flashTimeout = null;
    var frameCount = 0;

    var videoFeed = document.getElementById('video-feed');
    var videoPlaceholder = document.getElementById('video-placeholder');
    var stateValue = document.getElementById('state-value');
    var gestureFlags = document.getElementById('gesture-flags');
    var statusDot = document.getElementById('status-dot');
    var statusText = document.getElementById('status-text');
    var gestureLog = document.getElementById('gesture-log');
    var clickTestBtn = document.getElementById('click-test-btn');
    var dragBox = document.getElementById('drag-box');
    var dragContainer = document.getElementById('drag-container');

    function timestamp() {
        var d = new Date();
        return d.toLocaleTimeString('en-US', { hour12: false }) + '.' + String(d.getMilliseconds()).padStart(3, '0');
    }

    function addLog(message, type) {
        var entry = document.createElement('div');
        entry.className = 'log-entry type-' + type;
        entry.innerHTML = '<span class="log-timestamp">[' + timestamp() + ']</span>' + message;
        gestureLog.appendChild(entry);

        while (gestureLog.children.length > MAX_LOG_ENTRIES) {
            gestureLog.removeChild(gestureLog.firstChild);
        }

        gestureLog.scrollTop = gestureLog.scrollHeight;
    }

    function updateGestureFlags(gestures) {
        gestureFlags.innerHTML = '';
        var keys = Object.keys(gestures);
        for (var i = 0; i < keys.length; i++) {
            var key = keys[i];
            var flag = document.createElement('span');
            flag.className = 'gesture-flag' + (gestures[key] ? ' active' : '');
            flag.textContent = key;
            gestureFlags.appendChild(flag);
        }
    }

    socket.on('connect', function () {
        statusDot.className = 'status-dot connected';
        statusText.textContent = 'Connected';
        addLog('Socket connected', 'info');
        console.log('[SocketIO] Connected');
    });

    socket.on('disconnect', function () {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = 'Disconnected';
        addLog('Socket disconnected', 'info');
        console.log('[SocketIO] Disconnected');
    });

    socket.on('connect_error', function (err) {
        console.error('[SocketIO] Connection error:', err);
        addLog('Connection error: ' + err.message, 'info');
    });

    socket.on('video_frame', function (data) {
        frameCount++;
        if (frameCount === 1) {
            console.log('[SocketIO] First video frame received');
            addLog('Video stream started', 'info');
        }
        if (frameCount % 30 === 0) {
            console.log('[SocketIO] Received ' + frameCount + ' frames');
        }
        if (videoPlaceholder) {
            videoPlaceholder.style.display = 'none';
        }
        videoFeed.src = 'data:image/jpeg;base64,' + data.frame;
        videoFeed.style.display = 'block';
    });

    socket.on('gesture_state', function (data) {
        var newState = data.state;
        var newGestures = data.gestures || {};

        stateValue.textContent = newState;

        if (currentState !== newState) {
            addLog('State \u2192 ' + newState, 'state');
            currentState = newState;
        }

        var gestureKeys = Object.keys(newGestures);
        for (var i = 0; i < gestureKeys.length; i++) {
            var key = gestureKeys[i];
            if (currentGestures[key] !== undefined && currentGestures[key] !== newGestures[key]) {
                var label = newGestures[key] ? 'ON' : 'OFF';
                addLog('Gesture ' + key + ' \u2192 ' + label, 'gesture');
            }
        }

        currentGestures = newGestures;
        updateGestureFlags(newGestures);
    });

    function flashButton(className, duration) {
        if (flashTimeout) {
            clearTimeout(flashTimeout);
        }
        clickTestBtn.className = 'click-test-btn ' + className;
        flashTimeout = setTimeout(function () {
            clickTestBtn.className = 'click-test-btn';
        }, duration || 300);
    }

    clickTestBtn.addEventListener('click', function (e) {
        flashButton('flash-click', 300);
        addLog('Left Click', 'click');
    });

    clickTestBtn.addEventListener('dblclick', function (e) {
        flashButton('flash-dblclick', 400);
        addLog('Double Click', 'dblclick');
    });

    clickTestBtn.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        flashButton('flash-rightclick', 300);
        addLog('Right Click', 'rightclick');
    });

    var isDragging = false;
    var dragOffsetX = 0;
    var dragOffsetY = 0;
    var boxX = 0;
    var boxY = 0;

    function initDragPosition() {
        var containerRect = dragContainer.getBoundingClientRect();
        var boxRect = dragBox.getBoundingClientRect();
        boxX = (containerRect.width - boxRect.width) / 2;
        boxY = (containerRect.height - boxRect.height) / 2;
        dragBox.style.transform = 'translate(' + boxX + 'px, ' + boxY + 'px)';
    }

    dragBox.addEventListener('mousedown', function (e) {
        e.preventDefault();
        isDragging = true;
        dragBox.classList.add('dragging');
        var rect = dragBox.getBoundingClientRect();
        dragOffsetX = e.clientX - rect.left;
        dragOffsetY = e.clientY - rect.top;
    });

    document.addEventListener('mousemove', function (e) {
        if (!isDragging) return;
        var containerRect = dragContainer.getBoundingClientRect();
        var newX = e.clientX - containerRect.left - dragOffsetX;
        var newY = e.clientY - containerRect.top - dragOffsetY;
        var maxX = containerRect.width - dragBox.offsetWidth;
        var maxY = containerRect.height - dragBox.offsetHeight;
        boxX = Math.max(0, Math.min(maxX, newX));
        boxY = Math.max(0, Math.min(maxY, newY));
        dragBox.style.transform = 'translate(' + boxX + 'px, ' + boxY + 'px)';
    });

    document.addEventListener('mouseup', function () {
        if (isDragging) {
            isDragging = false;
            dragBox.classList.remove('dragging');
        }
    });

    window.addEventListener('load', function () {
        initDragPosition();
        addLog('Interface ready \u2014 waiting for connection', 'info');
        console.log('[App] Interface loaded, SocketIO connecting...');
    });

    window.addEventListener('resize', function () {
        if (!isDragging) {
            initDragPosition();
        }
    });
})();
