function process_logic(request) {
    function evaluateTest(e) {
        e.preventDefault();
        const hgb = document.getElementById('hemoglobin').value;
        const gender = document.getElementById('gender').value;
        const csrf = document.getElementById('csrf').value;
        const params = new URLSearchParams();
        params.append('hemoglobin', hgb);
        params.append('gender', gender);
        params.append('csrf_token', csrf);
        fetch('/api/evaluate', {
            method: 'POST',
            body: params,
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        }).then(r => r.json()).then(data => {
            const box = document.getElementById('resultBox');
            box.className = 'mt-4 text-center p-3 border rounded';
            if (data.error) {
                document.getElementById('resStatus').innerText = 'Error';
                document.getElementById('resMsg').innerText = data.error;
                box.classList.add('bg-danger-subtle', 'border-danger', 'text-danger');
                return;
            }
            document.getElementById('resStatus').innerText = 'Result: ' + data.status;
            document.getElementById('resMsg').innerText = data.message;
            box.classList.add('bg-' + data.color + '-subtle', 'border-' + data.color, 'text-' + data.color);
        });
    }
    request.context["evaluateTest"] = evaluateTest;
    return {};
}