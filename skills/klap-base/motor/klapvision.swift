// klapvision: recorte da pessoa (máscara) e posição do rosto, usando o Vision da Apple.
// Sem downloads, roda no próprio Mac.
//
//   klapvision matte <video.mp4> <mascara.mp4> [fast|balanced|accurate]
//       grava um vídeo em tons de cinza (branco = pessoa) do mesmo tamanho e fps
//   klapvision face <video.mp4> <face.json> [passo_segundos]
//       amostra o rosto a cada N s e grava {"frames":[{t,x,y,w,h}], "median":{x,y,w,h}} (0..1, origem no topo)

import AVFoundation
import CoreImage
import Foundation
import Vision

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(1)
}

func videoTrack(_ url: URL) -> (AVAsset, AVAssetTrack) {
    let asset = AVURLAsset(url: url)
    let sem = DispatchSemaphore(value: 0)
    var track: AVAssetTrack?
    Task {
        track = try? await asset.loadTracks(withMediaType: .video).first
        sem.signal()
    }
    sem.wait()
    guard let t = track else { fail("sem faixa de vídeo: \(url.path)") }
    return (asset, t)
}

func makeReader(_ asset: AVAsset, _ track: AVAssetTrack) -> (AVAssetReader, AVAssetReaderTrackOutput) {
    guard let reader = try? AVAssetReader(asset: asset) else { fail("não abriu o vídeo") }
    let out = AVAssetReaderTrackOutput(track: track, outputSettings: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    ])
    out.alwaysCopiesSampleData = false
    reader.add(out)
    reader.startReading()
    return (reader, out)
}

func matte(_ inPath: String, _ outPath: String, _ quality: String) {
    let (asset, track) = videoTrack(URL(fileURLWithPath: inPath))
    let size = track.naturalSize
    let w = Int(size.width), h = Int(size.height)
    let (reader, output) = makeReader(asset, track)

    let outURL = URL(fileURLWithPath: outPath)
    try? FileManager.default.removeItem(at: outURL)
    guard let writer = try? AVAssetWriter(outputURL: outURL, fileType: .mp4) else { fail("não criou a saída") }
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
        AVVideoCodecKey: AVVideoCodecType.h264,
        AVVideoWidthKey: w,
        AVVideoHeightKey: h,
        AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 8_000_000],
    ])
    input.expectsMediaDataInRealTime = false
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
        kCVPixelBufferWidthKey as String: w,
        kCVPixelBufferHeightKey as String: h,
    ])
    writer.add(input)
    writer.startWriting()
    writer.startSession(atSourceTime: .zero)

    let req = VNGeneratePersonSegmentationRequest()
    switch quality {
    case "fast": req.qualityLevel = .fast
    case "balanced": req.qualityLevel = .balanced
    default: req.qualityLevel = .accurate
    }
    req.outputPixelFormat = kCVPixelFormatType_OneComponent8
    let ctx = CIContext(options: [.useSoftwareRenderer: false])
    var n = 0
    while let sample = output.copyNextSampleBuffer() {
        guard let pb = CMSampleBufferGetImageBuffer(sample) else { continue }
        let pts = CMSampleBufferGetPresentationTimeStamp(sample)
        let handler = VNImageRequestHandler(cvPixelBuffer: pb, options: [:])
        try? handler.perform([req])
        var outBuf: CVPixelBuffer?
        CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &outBuf)
        guard let ob = outBuf else { continue }
        if let mask = req.results?.first?.pixelBuffer {
            let m = CIImage(cvPixelBuffer: mask)
            let sx = CGFloat(w) / m.extent.width, sy = CGFloat(h) / m.extent.height
            let scaled = m.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
            // tons de cinza -> RGB
            let rgb = scaled.applyingFilter("CIColorMatrix", parameters: [
                "inputRVector": CIVector(x: 1, y: 0, z: 0, w: 0),
                "inputGVector": CIVector(x: 1, y: 0, z: 0, w: 0),
                "inputBVector": CIVector(x: 1, y: 0, z: 0, w: 0),
                "inputAVector": CIVector(x: 0, y: 0, z: 0, w: 1),
            ])
            ctx.render(rgb, to: ob, bounds: CGRect(x: 0, y: 0, width: w, height: h), colorSpace: CGColorSpaceCreateDeviceRGB())
        }
        while !input.isReadyForMoreMediaData { usleep(2000) }
        adaptor.append(ob, withPresentationTime: pts)
        n += 1
        if n % 60 == 0 { print("matte \(n) quadros"); fflush(stdout) }
    }
    if reader.status == .failed { fail("erro lendo: \(String(describing: reader.error))") }
    input.markAsFinished()
    let sem = DispatchSemaphore(value: 0)
    writer.finishWriting { sem.signal() }
    sem.wait()
    if writer.status != .completed { fail("erro gravando: \(String(describing: writer.error))") }
    print("ok \(n) quadros -> \(outPath)")
}

func face(_ inPath: String, _ outPath: String, _ step: Double) {
    let (asset, track) = videoTrack(URL(fileURLWithPath: inPath))
    let (_, output) = makeReader(asset, track)
    var frames: [[String: Double]] = []
    var next = 0.0
    while let sample = output.copyNextSampleBuffer() {
        let t = CMSampleBufferGetPresentationTimeStamp(sample).seconds
        if t + 1e-6 < next { continue }
        next = t + step
        guard let pb = CMSampleBufferGetImageBuffer(sample) else { continue }
        let req = VNDetectFaceRectanglesRequest()
        try? VNImageRequestHandler(cvPixelBuffer: pb, options: [:]).perform([req])
        guard let faces = req.results, !faces.isEmpty else { continue }
        let f = faces.max(by: { $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height })!
        let b = f.boundingBox  // origem embaixo-esquerda
        frames.append(["t": t, "x": b.minX, "y": 1 - b.maxY, "w": b.width, "h": b.height])
    }
    func med(_ k: String) -> Double {
        let v = frames.map { $0[k]! }.sorted()
        return v.isEmpty ? 0 : v[v.count / 2]
    }
    var result: [String: Any] = ["frames": frames]
    if frames.isEmpty {
        result["median"] = ["x": 0.35, "y": 0.18, "w": 0.3, "h": 0.2]
        result["found"] = false
    } else {
        result["median"] = ["x": med("x"), "y": med("y"), "w": med("w"), "h": med("h")]
        result["found"] = true
    }
    let data = try! JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted])
    try! data.write(to: URL(fileURLWithPath: outPath))
    print("ok \(frames.count) amostras -> \(outPath)")
}

let a = CommandLine.arguments
guard a.count >= 4 else { fail("uso: klapvision matte|face <entrada> <saida> [opção]") }
switch a[1] {
case "matte": matte(a[2], a[3], a.count > 4 ? a[4] : "accurate")
case "face": face(a[2], a[3], a.count > 4 ? Double(a[4]) ?? 0.5 : 0.5)
default: fail("comando desconhecido: \(a[1])")
}
