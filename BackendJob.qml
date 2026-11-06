import QtQuick

// Запрос к постоянному бэкенду (backend/run.py serve) с тем же видом, что у Process:
// command = [скрипт, команда, аргументы…], running = true — отправить, по ответу running
// снова false и сигнал exited(code); stdout/stderr — в out / err. ranCommand — с чем запустили
// (command мог поменяться, пока ждали ответ). running=false и сразу true — новый запрос,
// ответ на старый игнорируется.
QtObject {
  id: job
  property var host                 // Customizer: host.call(args, callback)
  property var command: []
  property bool running: false
  property var ranCommand: []
  property string out: ""
  property string err: ""
  property int gen: 0
  signal exited(int code)

  onRunningChanged: {
    if (!running) return
    var g = ++job.gen
    job.ranCommand = job.command.slice()
    host.call(job.command.slice(1), function(r) {
      if (g !== job.gen || !job.running) return
      job.out = r.out || ""
      job.err = r.err || ""
      job.running = false
      job.exited(r.code)
    })
  }
}
