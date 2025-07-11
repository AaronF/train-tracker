function fetch_trains(){
	fetch('/trains')
		.then(response => response.json())
		.then(data => {
			const output = document.getElementById('output');
			output.innerHTML = data.map(train => `<li>${train.train_id}</li>`)
		})
}

setInterval(fetch_trains, 10000);
fetch_trains();