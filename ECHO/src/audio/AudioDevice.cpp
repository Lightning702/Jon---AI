#include "AudioDevice.h"
#include "../core/Log.h"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <avrt.h>

namespace echo {

namespace {

const CLSID kMMDeviceEnumerator = __uuidof(MMDeviceEnumerator);
const IID kIMMDeviceEnumerator = __uuidof(IMMDeviceEnumerator);
const IID kIAudioClient = __uuidof(IAudioClient);
const IID kIAudioRenderClient = __uuidof(IAudioRenderClient);

}

unsigned long __stdcall AudioDevice::threadEntry(void* param) {
    ((AudioDevice*)param)->threadMain();
    return 0;
}

void AudioDevice::threadMain() {
    HRESULT hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    bool comInit = SUCCEEDED(hr);

    IMMDeviceEnumerator* enumerator = nullptr;
    IMMDevice* device = nullptr;
    IAudioClient* client = nullptr;
    IAudioRenderClient* render = nullptr;
    WAVEFORMATEX* mixFormat = nullptr;
    HANDLE bufferEvent = nullptr;
    HANDLE mmcssHandle = nullptr;
    DWORD taskIndex = 0;

    hr = CoCreateInstance(kMMDeviceEnumerator, nullptr, CLSCTX_ALL, kIMMDeviceEnumerator, (void**)&enumerator);
    if (FAILED(hr)) { LOG_ERROR("Audio: device enumerator failed"); goto cleanup; }

    hr = enumerator->GetDefaultAudioEndpoint(eRender, eConsole, &device);
    if (FAILED(hr)) { LOG_ERROR("Audio: no default endpoint"); goto cleanup; }

    hr = device->Activate(kIAudioClient, CLSCTX_ALL, nullptr, (void**)&client);
    if (FAILED(hr)) { LOG_ERROR("Audio: activate failed"); goto cleanup; }

    hr = client->GetMixFormat(&mixFormat);
    if (FAILED(hr)) { LOG_ERROR("Audio: mix format failed"); goto cleanup; }

    rate = (int)mixFormat->nSamplesPerSec;
    chans = (int)mixFormat->nChannels;

    bufferEvent = CreateEventA(nullptr, FALSE, FALSE, nullptr);
    if (!bufferEvent) goto cleanup;

    hr = client->Initialize(AUDCLNT_SHAREMODE_SHARED,
                            AUDCLNT_STREAMFLAGS_EVENTCALLBACK | AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM | AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY,
                            2000000, 0, mixFormat, nullptr);
    if (FAILED(hr)) { LOG_ERROR("Audio: initialize failed 0x%08X", (unsigned)hr); goto cleanup; }

    hr = client->SetEventHandle(bufferEvent);
    if (FAILED(hr)) goto cleanup;

    hr = client->GetService(kIAudioRenderClient, (void**)&render);
    if (FAILED(hr)) goto cleanup;

    UINT32 bufferFrames;
    if (FAILED(client->GetBufferSize(&bufferFrames))) goto cleanup;

    mmcssHandle = AvSetMmThreadCharacteristicsA("Pro Audio", &taskIndex);

    {
        BYTE* data = nullptr;
        if (SUCCEEDED(render->GetBuffer(bufferFrames, &data))) {
            render->ReleaseBuffer(bufferFrames, AUDCLNT_BUFFERFLAGS_SILENT);
        }
    }

    if (FAILED(client->Start())) goto cleanup;

    LOG_INFO("Audio started: %d Hz, %d channels, %u frame buffer", rate, chans, bufferFrames);
    active = true;

    while (WaitForSingleObject((HANDLE)stopEvent, 0) != WAIT_OBJECT_0) {
        DWORD wait = WaitForSingleObject(bufferEvent, 200);
        if (wait != WAIT_OBJECT_0) continue;

        UINT32 padding = 0;
        if (FAILED(client->GetCurrentPadding(&padding))) break;
        UINT32 available = bufferFrames - padding;
        if (available == 0) continue;

        BYTE* data = nullptr;
        if (FAILED(render->GetBuffer(available, &data))) break;

        if (callback) callback((float*)data, (int)available, chans);
        else std::memset(data, 0, (size_t)available * chans * sizeof(float));

        render->ReleaseBuffer(available, 0);
    }

    client->Stop();

cleanup:
    active = false;
    if (mmcssHandle) AvRevertMmThreadCharacteristics(mmcssHandle);
    if (render) render->Release();
    if (mixFormat) CoTaskMemFree(mixFormat);
    if (client) client->Release();
    if (device) device->Release();
    if (enumerator) enumerator->Release();
    if (bufferEvent) CloseHandle(bufferEvent);
    if (comInit) CoUninitialize();
}

bool AudioDevice::start(const RenderCallback& cb) {
    if (thread) return true;
    callback = cb;
    stopEvent = CreateEventA(nullptr, TRUE, FALSE, nullptr);
    if (!stopEvent) return false;
    thread = CreateThread(nullptr, 0, threadEntry, this, 0, nullptr);
    if (!thread) {
        CloseHandle((HANDLE)stopEvent);
        stopEvent = nullptr;
        return false;
    }
    SetThreadPriority((HANDLE)thread, THREAD_PRIORITY_TIME_CRITICAL);
    for (int i = 0; i < 200 && !active; i++) Sleep(5);
    return true;
}

void AudioDevice::stop() {
    if (!thread) return;
    SetEvent((HANDLE)stopEvent);
    WaitForSingleObject((HANDLE)thread, 2000);
    CloseHandle((HANDLE)thread);
    CloseHandle((HANDLE)stopEvent);
    thread = nullptr;
    stopEvent = nullptr;
    active = false;
}

}
