const line_1 = "0021|0023|0026,0027|0608,0039|0042,0045|0046,0049|0052,0053|0066,0067|0074,0081|0191|0192,0195,K195|0196,0201,W201|0202,0205|0206|0212,0209|0216,0221";
const line_2 = "0022|0024|0028,0607|0034|0044,0047|0048,0051|0054,0055|0068,0069|0076,0083|0193|0194,0197|0198,0203|0204,0207,K204|0208,W208|0214,0211|0218,0223";
const line_3 = "6059|6061|6064,6063|6055|6072,6073|6076,6075|6082,6079|6086|6096,0057|0070,0071|3951|3953|3955|3957|3959|3975|3977";
const line_4 = "6058|6060|6066,6069|6074|6080|6084|6090,6083|6092|6098,0059|0072,0093|0078|3952|3954|3958|3962,3973|3970|3974|3976";

document.addEventListener('DOMContentLoaded', () => {
	const pad2 = (n) => String(n).padStart(2, '0');
	const splitSegments = (s) => s.split('|'); // only split on pipes

	const lines = [
		{ node: document.getElementById('line_1'), segments: splitSegments(line_1) },
		{ node: document.getElementById('line_2'), segments: splitSegments(line_2) },
		{ node: document.getElementById('line_3'), segments: splitSegments(line_3) },
		{ node: document.getElementById('line_4'), segments: splitSegments(line_4) },
	];

	// Build dots + a fast lookup
	const segmentMap = {};
	let segIndex = 0;

	for (const line of lines) {
		if (!line?.node) continue;
		const frag = document.createDocumentFragment();

		for (const _ of line.segments) {
			const id = `SEG${pad2(segIndex++)}`;
			const dot = document.createElement('div');
			dot.id = id;
			dot.className = 'segment block h-6 w-14 px-1 rounded-full bg-white text-sm leading-6 text-center text-black [&.active]:bg-green-300';
			frag.appendChild(dot);
			segmentMap[id] = dot; // build map as we go
		}
		line.node.appendChild(frag);
	}

	// --- MQTT ---
	const cfg = window.MQTT_CONFIG || {};
	if (!cfg.host || !cfg.port) {
		console.error('MQTT_CONFIG missing host/port');
		return;
	}

	const mqtt_url = `${cfg.secure ? 'wss' : 'ws'}://${cfg.host}:${cfg.port}`;
	const client = mqtt.connect(mqtt_url, {
		keepalive: 60,
		username: cfg.username,
		password: cfg.password,
		reconnectPeriod: 2000,
	});

	client.on('connect', () => {
		console.log('Connected to broker');
		client.subscribe('trains/segments', { qos: 0 }); // tweak QoS if needed
	});

	// Optional: clear stale state before applying updates
	const clearAll = () => {
		for (const el of Object.values(segmentMap)) {
			el.classList.remove('active');
			el.textContent = '';
		}
	};

	client.on('message', (_topic, message) => {
		let data;
		try {
			data = JSON.parse(message.toString());
		} catch {
			console.error('Invalid JSON:', message.toString());
			return;
		}

		if (!data || typeof data !== 'object') return;

		// If payload is full-state, uncomment next line to avoid stale actives:
		// clearAll();

		for (const [key, value] of Object.entries(data)) {
			const el = segmentMap[key];
			if (!el) continue;

			const trains = Array.isArray(value?.trains) ? value.trains : [];
			if (trains.length > 0) {
				el.classList.add('active');
				el.textContent = String(trains[0]);
			} else {
				el.classList.remove('active');
				el.textContent = '';
			}
		}
	});

	// Clean up on page exit
	window.addEventListener('beforeunload', () => {
		try { client.end(true); } catch { }
	});
});